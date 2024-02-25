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

import copy
import os
import re
import time
import urllib.request as urllib2
import yaml

from kubernetes import client
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import uuidutils
from toscaparser import tosca_template

from tacker._i18n import _
from tacker.api.vnflcm.v1.controller import check_vnf_state
from tacker.common.container import kubernetes_utils
from tacker.common import exceptions
from tacker.common import log
from tacker.common import utils
from tacker.extensions import vnfm
from tacker import objects
from tacker.objects import fields
from tacker.objects.fields import ErrorPoint as EP
from tacker.objects import vnf_package as vnf_package_obj
from tacker.objects import vnf_package_vnfd as vnfd_obj
from tacker.objects import vnf_resources as vnf_resource_obj
from tacker.tosca import utils as toscautils  # TODO(yasufum)
from tacker.vnflcm import utils as vnflcm_utils
from tacker.vnfm.infra_drivers import abstract_driver
from tacker.vnfm.infra_drivers.kubernetes.helm import helm_client
from tacker.vnfm.infra_drivers.kubernetes.k8s import translate_outputs
from tacker.vnfm.infra_drivers.kubernetes import utils as k8s_utils
from tacker.vnfm.infra_drivers import scale_driver
from urllib.parse import urlparse


CNF_TARGET_FILES_KEY = 'lcm-kubernetes-def-files'
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
VNFC_POD_NOT_FOUND = "POD_NOT_FOUND"

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

HELM_CHART_DIR_BASE = "/var/tacker/helm"


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
        self.CHECK_DICT_KEY = [
            "Pod",
            "Service",
            "PersistentVolumeClaim",
            "Namespace",
            "Node",
            "PersistentVolume",
            "APIService",
            "DaemonSet",
            "Deployment",
            "ReplicaSet",
            "StatefulSet",
            "Job",
            "VolumeAttachment"
        ]

    def get_type(self):
        return 'kubernetes'

    def get_name(self):
        return 'kubernetes'

    def get_description(self):
        return 'Kubernetes infra driver'

    def create(self, plugin, context, vnf):
        # NOTE: This method was used for Legacy API, and leave this method
        #       because define as abstractmethod in super class.
        pass

    def create_wait(self, plugin, context, vnf_dict, vnf_id, auth_attr):
        pass

    def create_wait_k8s(self, k8s_objs, k8s_client_dict, vnf_instance):
        try:
            time.sleep(self.STACK_RETRY_WAIT)
            keep_going = True
            stack_retries = self.STACK_RETRIES
            while keep_going and stack_retries > 0:
                for k8s_obj in k8s_objs:
                    kind = k8s_obj.get('object').kind
                    namespace = k8s_obj.get('namespace')
                    if hasattr(k8s_obj.get('object').metadata, 'name'):
                        name = k8s_obj.get('object').metadata.name
                    else:
                        name = ''
                    api_version = k8s_obj.get('object').api_version
                    if k8s_obj.get('status') == 'Creating':
                        if kind in self.CHECK_DICT_KEY:
                            check_method = self.\
                                _select_check_status_by_kind(kind)
                            check_method(k8s_client_dict, k8s_obj,
                                         namespace, name, api_version)
                        else:
                            k8s_obj['status'] = 'Create_complete'

                keep_going = False
                for k8s_obj in k8s_objs:
                    if k8s_obj.get('status') != 'Create_complete':
                        keep_going = True
                    else:
                        if k8s_obj.get('object', '').metadata:
                            LOG.debug(
                                'Resource namespace: {namespace},'
                                'name:{name},kind: {kind} '
                                'is create complete'.format(
                                    namespace=k8s_obj.get('namespace'),
                                    name=k8s_obj.get('object').metadata.name,
                                    kind=k8s_obj.get('object').kind)
                            )
                        else:
                            LOG.debug(
                                'Resource namespace: {namespace},'
                                'name:{name},kind: {kind} '
                                'is create complete'.format(
                                    namespace=k8s_obj.get('namespace'),
                                    name='',
                                    kind=k8s_obj.get('object').kind)
                            )
                if keep_going:
                    time.sleep(self.STACK_RETRY_WAIT)
                    stack_retries -= 1
            if stack_retries == 0 and keep_going:
                LOG.error('It is time out, When instantiate cnf,'
                          'waiting for resource creation.')
                for k8s_obj in k8s_objs:
                    if k8s_obj.get('status') == 'Creating':
                        k8s_obj['status'] = 'Wait_failed'
                        err_reason = _("The resources are creating time out."
                                       "namespace: {namespace}, name:{name}, "
                                       "kind: {kind}).Reason: {message}").\
                            format(namespace=k8s_obj.get('namespace'),
                                   name=k8s_obj.get('object').metadata.name,
                                   kind=k8s_obj.get('object').kind,
                                   message=k8s_obj['message'])
                        LOG.error(err_reason)
                error_reason = _(
                    "Resource creation is not completed within"
                    " {wait} seconds as creation of stack {stack}"
                    " is not completed").format(
                    wait=(self.STACK_RETRIES * self.STACK_RETRY_WAIT),
                    stack=vnf_instance.id
                )
                raise vnfm.CNFCreateWaitFailed(reason=error_reason)
            return k8s_objs
        except Exception as e:
            LOG.error('Creating wait CNF got an error due to %s', e)
            raise e

    def _select_check_status_by_kind(self, kind):
        check_dict = {
            "Pod": self._check_status_pod,
            "Service": self._check_status_service,
            "PersistentVolumeClaim":
                self._check_status_persistent_volume_claim,
            "Namespace": self._check_status_namespace,
            "Node": self._check_status_node,
            "PersistentVolume": self._check_status_persistent_volume,
            "APIService": self._check_status_api_service,
            "DaemonSet": self._check_status_daemon_set,
            "Deployment": self._check_status_deployment,
            "ReplicaSet": self._check_status_replica_set,
            "StatefulSet": self._check_status_stateful_set,
            "Job": self._check_status_job,
            "VolumeAttachment": self._check_status_volume_attachment
        }
        return check_dict[kind]

    def _check_is_ip(self, ip_str):
        if re.match(r'^\d{,3}.\d{,3}.\d{,3}.\d{,3}$', ip_str):
            num_list = [int(x) for x in ip_str.split('.')]
            for i in num_list:
                if i > 255 or i < 0:
                    return False
            return True
        else:
            return False

    def _check_status_stateful_set(self, k8s_client_dict, k8s_obj,
                                   namespace, name, api_version):
        stateful_set = k8s_client_dict[api_version]. \
            read_namespaced_stateful_set(namespace=namespace, name=name)
        if stateful_set.status.replicas != \
                stateful_set.status.ready_replicas:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Pod in StatefulSet is still creating. " \
                                 "The pod is ready {value1}/{value2}".format(
                value1=stateful_set.status.ready_replicas,
                value2=stateful_set.status.replicas
            )
        else:
            for i in range(0, stateful_set.spec.replicas):
                volume_claim_templates = stateful_set.spec.\
                    volume_claim_templates
                if volume_claim_templates is None:
                    k8s_obj['status'] = 'Create_complete'
                    k8s_obj['message'] = 'StatefulSet is created'
                    break
                for volume_claim_template in volume_claim_templates:
                    pvc_name = "-".join(
                        [volume_claim_template.metadata.name, name, str(i)])
                    persistent_volume_claim = k8s_client_dict['v1']. \
                        read_namespaced_persistent_volume_claim(
                        namespace=namespace, name=pvc_name)
                    if persistent_volume_claim.status.phase != 'Bound':
                        k8s_obj['status'] = 'Creating'
                        k8s_obj['message'] = "PersistentVolumeClaim in " \
                                             "StatefulSet is still " \
                                             "creating." \
                                             "The status is " \
                                             "{status}".format(
                            status=persistent_volume_claim.status.phase)
                else:
                    k8s_obj['status'] = 'Create_complete'
                    k8s_obj['message'] = 'StatefulSet is created'

    def _check_status_pod(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        pod = k8s_client_dict[api_version].read_namespaced_pod(
            namespace=namespace, name=name)
        if pod.status.phase != 'Running':
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Pod is still creating. The status is " \
                                 "{status}".format(status=pod.
                                                   status.phase)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "Pod is created"

    def _check_status_service(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        service = k8s_client_dict[api_version].read_namespaced_service(
            namespace=namespace, name=name)
        status_flag = False
        if service.spec.cluster_ip == "None" or \
                self._check_is_ip(service.spec.cluster_ip):
            try:
                endpoint = k8s_client_dict['v1'].\
                    read_namespaced_endpoints(namespace=namespace, name=name)
                if endpoint:
                    status_flag = True
            except Exception as e:
                msg = _('read endpoinds failed.kind:{kind}.reason:{e}'.format(
                    kind=service.kind, e=e))
                LOG.error(msg)
                raise exceptions.ReadEndpoindsFalse(error=msg)
        if status_flag:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "Service is created"
        else:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Service is still creating." \
                                 "The status is False"

    def _check_status_persistent_volume_claim(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        claim = k8s_client_dict[api_version].\
            read_namespaced_persistent_volume_claim(
            namespace=namespace, name=name)
        if claim.status.phase != 'Bound':
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "PersistentVolumeClaim is still creating."\
                                 "The status is {status}".\
                format(status=claim.status.phase)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "PersistentVolumeClaim is created"

    def _check_status_namespace(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        name_space = k8s_client_dict[api_version].read_namespace(name=name)
        if name_space.status.phase != 'Active':
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Namespace is still creating." \
                                 "The status is {status}". \
                format(status=name_space.status.phase)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "Namespace is created"

    def _check_status_node(self, k8s_client_dict, k8s_obj,
                          namespace, name, api_version):
        node = k8s_client_dict[api_version].read_node(name=name)
        status_flag = False
        for condition in node.status.conditions:
            if condition.type == 'Ready':
                if condition.status == 'True':
                    status_flag = True
                    break
            else:
                continue
        if status_flag:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "Node is created"
        else:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Node is still creating." \
                                 "The status is False"

    def _check_status_persistent_volume(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        volume = k8s_client_dict[api_version].\
            read_persistent_volume(name=name)
        if volume.status.phase != 'Available' and \
                volume.status.phase != 'Bound':
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "PersistentVolume is still creating." \
                                 "The status is {status}". \
                format(status=volume.status.phase)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "PersistentVolume is created"

    def _check_status_api_service(self, k8s_client_dict, k8s_obj,
                               namespace, name, api_version):
        api_service = k8s_client_dict[api_version].read_api_service(name=name)
        status_flag = False
        for condition in api_service.status.conditions:
            if condition.type == 'Available':
                if condition.status == 'True':
                    status_flag = True
                    break
            else:
                continue
        if status_flag:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = "APIService is created"
        else:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "APIService is still creating." \
                                 "The status is False"

    def _check_status_daemon_set(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        daemon_set = k8s_client_dict[api_version].\
            read_namespaced_daemon_set(namespace=namespace, name=name)
        if daemon_set.status.desired_number_scheduled != \
                daemon_set.status.number_ready:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "DaemonSet is still creating. " \
                                 "The DaemonSet is ready {value1}/{value2}".\
                format(value1=daemon_set.status.number_ready,
                       value2=daemon_set.status.desired_number_scheduled)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = 'DaemonSet is created'

    def _check_status_deployment(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        deployment = k8s_client_dict[api_version].\
            read_namespaced_deployment(namespace=namespace, name=name)
        if deployment.status.replicas != deployment.status.ready_replicas:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Deployment is still creating. " \
                                 "The Deployment is ready {value1}/{value2}".\
                format(value1=deployment.status.ready_replicas,
                       value2=deployment.status.replicas
                       )
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = 'Deployment is created'

    def _check_status_replica_set(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        replica_set = k8s_client_dict[api_version].\
            read_namespaced_replica_set(namespace=namespace, name=name)
        if replica_set.status.replicas != replica_set.status.ready_replicas:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "ReplicaSet is still creating. " \
                                 "The ReplicaSet is ready {value1}/{value2}".\
                format(value1=replica_set.status.ready_replicas,
                       value2=replica_set.status.replicas
                       )
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = 'ReplicaSet is created'

    def _check_status_job(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        job = k8s_client_dict[api_version].\
            read_namespaced_job(namespace=namespace, name=name)
        if job.spec.completions != job.status.succeeded:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "Job is still creating." \
                                 "The status is {status}". \
                format(status=job.spec.completions)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = 'Job is created'

    def _check_status_volume_attachment(self, k8s_client_dict, k8s_obj,
                         namespace, name, api_version):
        volume = k8s_client_dict[api_version].\
            read_volume_attachment(name=name)
        if not volume.status.attached:
            k8s_obj['status'] = 'Creating'
            k8s_obj['message'] = "VolumeAttachment is still creating." \
                                 "The status is {status}". \
                format(status=volume.status.attached)
        else:
            k8s_obj['status'] = 'Create_complete'
            k8s_obj['message'] = 'VolumeAttachment is created'

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

    def get_pod_status(self, pods_information):
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
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
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

    def _select_delete_api(self, k8s_client_dict, namespace, name,
                           kind, api_version, body):
        """select kubernetes delete api and call"""
        def convert(name):
            name_with_underscores = re.sub(
                '(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                          name_with_underscores).lower()

        snake_case_kind = convert(kind)
        kubernetes = translate_outputs.Transformer(
            None, None, None, None)
        try:
            if 'namespaced' in kubernetes.method_value.get(kind):
                delete_api = eval('k8s_client_dict[api_version].'
                                  'delete_namespaced_%s' % snake_case_kind)
                response = delete_api(name=name, namespace=namespace,
                                      body=body)
            else:
                delete_api = eval('k8s_client_dict[api_version].'
                                  'delete_%s' % snake_case_kind)
                response = delete_api(name=name, body=body)
        except Exception:
            raise

        return response

    def _get_pvc_list_for_delete(self, k8s_client_dict, sfs_name, namespace):
        pvc_list_for_delete = list()
        try:
            resp_read_sfs = k8s_client_dict['apps/v1'].\
                read_namespaced_stateful_set(sfs_name, namespace)
            sfs_spec = resp_read_sfs.spec
            volume_claim_templates = list()
            volume_claim_templates = sfs_spec.volume_claim_templates

            try:
                resp_list_pvc = k8s_client_dict['v1'].\
                    list_namespaced_persistent_volume_claim(namespace)
                pvc_list = resp_list_pvc.items
                for volume_claim_template in volume_claim_templates:
                    pvc_template_metadata = volume_claim_template.metadata
                    match_pattern = '-'.join(
                        [pvc_template_metadata.name, sfs_name, ""])

                    for pvc in pvc_list:
                        pvc_metadata = pvc.metadata
                        pvc_name = pvc_metadata.name
                        match_result = re.match(
                            match_pattern + '[0-9]+$', pvc_name)
                        if match_result is not None:
                            pvc_list_for_delete.append(pvc_name)
            except Exception as e:
                LOG.debug(e)
                pass
        except Exception as e:
            LOG.debug(e)
            pass
        return pvc_list_for_delete

    @log.log
    def _delete_k8s_obj(self, kind, k8s_client_dict, vnf_resource, body,
                        namespace):
        name = vnf_resource.resource_name
        api_version = vnf_resource.resource_type.\
            split(COMMA_CHARACTER)[0]

        pvc_list_for_delete = list()
        # if kind is StatefulSet, create name list for deleting
        # PersistentVolumeClaim created when StatefulSet is generated.
        if kind == 'StatefulSet':
            pvc_list_for_delete = \
                self._get_pvc_list_for_delete(
                    k8s_client_dict=k8s_client_dict,
                    sfs_name=name,
                    namespace=namespace)

        # delete target k8s obj
        try:
            self._select_delete_api(
                k8s_client_dict=k8s_client_dict,
                namespace=namespace,
                name=name,
                kind=kind,
                api_version=api_version,
                body=body)
            LOG.debug('Successfully deleted resource: '
                      'kind=%(kind)s, name=%(name)s',
                      {"kind": kind, "name": name})
        except Exception as e:
            LOG.debug(e)
            pass

        if (kind == 'StatefulSet' and
                len(pvc_list_for_delete) > 0):
            for delete_pvc_name in pvc_list_for_delete:
                try:
                    k8s_client_dict['v1'].\
                        delete_namespaced_persistent_volume_claim(
                            name=delete_pvc_name,
                            namespace=namespace,
                            body=body)
                except Exception as e:
                    LOG.debug(e)
                    pass

    def _get_helm_info(self, vim_connection_info):
        # replace single quote to double quote
        helm_info = vim_connection_info.extra.get('helm_info')
        if isinstance(helm_info, str):
            helm_info = jsonutils.loads(helm_info.replace("'", '"'))
        ips = helm_info.get('masternode_ip', [])
        username = helm_info.get('masternode_username', '')
        password = helm_info.get('masternode_password', '')
        return ips, username, password

    def _helm_uninstall(self, context, vnf_instance):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        additional_params = inst_vnf_info.additional_params
        namespace = vnf_instance.vnf_metadata['namespace']
        helm_inst_param_list = additional_params.get(
            'using_helm_install_param')
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)
        ips, username, password = self._get_helm_info(vim_connection_info)
        k8s_objs = []
        # initialize HelmClient
        helmclient = helm_client.HelmClient(ips[0], username, password)
        for helm_inst_params in helm_inst_param_list:
            release_name = helm_inst_params.get('helmreleasename')
            # execute `helm uninstall` command
            helmclient.uninstall(release_name, namespace)
        helmclient.close_session()
        return k8s_objs

    @log.log
    def delete(self, plugin, context, vnf_id, auth_attr, region_name=None,
               vnf_instance=None, terminate_vnf_req=None):
        """Delete function"""
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        try:
            # check use_helm flag
            inst_vnf_info = vnf_instance.instantiated_vnf_info
            if self._is_use_helm_flag(inst_vnf_info.additional_params):
                self._helm_uninstall(context, vnf_instance)
                return
            # initialize Kubernetes APIs
            k8s_client_dict = self.kubernetes.\
                get_k8s_client_dict(auth=auth_cred)
            # get V1DeleteOptions for deleting an API object
            body = {}
            vnf_resources = objects.VnfResourceList.get_by_vnf_instance_id(
                context, vnf_instance.id)
            if terminate_vnf_req:
                if terminate_vnf_req.termination_type == 'GRACEFUL':
                    grace_period_seconds = terminate_vnf_req.\
                        graceful_termination_timeout
                elif terminate_vnf_req.termination_type == 'FORCEFUL':
                    grace_period_seconds = 0

                body = client.V1DeleteOptions(
                    propagation_policy='Foreground',
                    grace_period_seconds=grace_period_seconds)
            else:
                body = client.V1DeleteOptions(
                    propagation_policy='Foreground')

            # follow the order below to resolve dependency when deleting
            ordered_kind = [
                # 1.
                'Deployment', 'Job', 'DaemonSet', 'StatefulSet',
                # 2.
                'Pod',
                # 3.
                'PersistentVolumeClaim', 'ConfigMap', 'Secret',
                'PriorityClass',
                # 4.
                'PersistentVolume',
                # 5.
                'StorageClass',
                # 6. Except for 1 to 5 above, delete before `Namespace`
                'Service', 'LimitRange', 'PodTemplate', 'Node',
                'ResourceQuota', 'ServiceAccount', 'APIService',
                'ReplicaSet', 'ControllerRevision',
                'HorizontalPodAutoscaler', 'Lease', 'NetworkPolicy',
                'ClusterRole', 'ClusterRoleBinding', 'Role', 'RoleBinding',
                'VolumeAttachment',
                # 7. Delete `Namespace` finally
                'Namespace'
            ]
            namespace = vnf_instance.vnf_metadata['namespace']
            for kind in ordered_kind:
                for vnf_resource in vnf_resources:
                    obj_kind = vnf_resource.resource_type.\
                        split(COMMA_CHARACTER)[1]
                    if obj_kind == kind:
                        self._delete_k8s_obj(
                            kind=obj_kind,
                            k8s_client_dict=k8s_client_dict,
                            vnf_resource=vnf_resource,
                            body=body, namespace=namespace)
        except Exception as e:
            LOG.error('Deleting VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def select_k8s_obj_read_api(self, k8s_client_dict, namespace, name,
                                kind, api_version):
        """select kubernetes read api and call"""
        def convert(name):
            name_with_underscores = re.sub(
                '(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                          name_with_underscores).lower()

        snake_case_kind = convert(kind)
        kubernetes = translate_outputs.Transformer(None, None, None, None)
        try:
            if 'namespaced' in kubernetes.method_value.get(kind):
                read_api = eval('k8s_client_dict[api_version].'
                                'read_namespaced_%s' % snake_case_kind)
                response = read_api(name=name, namespace=namespace)
            else:
                read_api = eval('k8s_client_dict[api_version].'
                                'read_%s' % snake_case_kind)
                response = read_api(name=name)
        except Exception:
            raise

        return response

    def _post_helm_uninstall(self, context, vnf_instance):
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        additional_params = inst_vnf_info.additional_params
        helm_inst_param_list = additional_params.get(
            'using_helm_install_param')
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)
        ips, username, password = self._get_helm_info(vim_connection_info)
        del_dir = os.path.join(HELM_CHART_DIR_BASE, vnf_instance.id)
        for ip in ips:
            local_helm_del_flag = False
            # initialize HelmClient
            helmclient = helm_client.HelmClient(ip, username, password)
            for inst_params in helm_inst_param_list:
                if self._is_exthelmchart(inst_params):
                    repo_name = inst_params.get('helmrepositoryname')
                    # execute `helm repo add` command
                    helmclient.remove_repository(repo_name)
                else:
                    local_helm_del_flag = True
            if local_helm_del_flag:
                helmclient.delete_helmchart(del_dir)
            helmclient.close_session()

    @log.log
    def delete_wait(self, plugin, context, vnf_id, auth_attr,
                    region_name=None, vnf_instance=None):
        """Delete wait function

        This function is used to checking a containerized VNF is deleted
        completely or not. We do it by get information of Kubernetes objects.
        When Tacker can not get any information about service, the VNF will be
        marked as deleted.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)

        try:
            vnf_resources = objects.VnfResourceList.\
                get_by_vnf_instance_id(context, vnf_instance.id)
            k8s_client_dict = self.kubernetes.\
                get_k8s_client_dict(auth=auth_cred)
            namespace = vnf_instance.vnf_metadata['namespace']

            keep_going = True
            stack_retries = self.STACK_RETRIES

            while keep_going and stack_retries > 0:
                count = 0

                for vnf_resource in vnf_resources:
                    name = vnf_resource.resource_name
                    api_version = vnf_resource.resource_type.\
                        split(COMMA_CHARACTER)[0]
                    kind = vnf_resource.resource_type.\
                        split(COMMA_CHARACTER)[1]

                    if not k8s_client_dict.get(api_version):
                        continue
                    try:
                        self.select_k8s_obj_read_api(
                            k8s_client_dict=k8s_client_dict,
                            namespace=namespace,
                            name=name,
                            kind=kind,
                            api_version=api_version)
                        count = count + 1
                    except Exception:
                        pass

                stack_retries = stack_retries - 1
                # If one of objects is still alive, keeps on waiting
                if count > 0:
                    keep_going = True
                    time.sleep(self.STACK_RETRY_WAIT)
                else:
                    keep_going = False

            # check use_helm flag
            inst_vnf_info = vnf_instance.instantiated_vnf_info
            if self._is_use_helm_flag(inst_vnf_info.additional_params):
                self._post_helm_uninstall(context, vnf_instance)
        except Exception as e:
            LOG.error('Deleting wait VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def _call_read_scale_api(self, app_v1_api_client, namespace, name, kind):
        """select kubernetes read scale api and call"""
        def convert(name):
            name_with_underscores = re.sub(
                '(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                        name_with_underscores).lower()
        snake_case_kind = convert(kind)
        try:
            read_scale_api = eval('app_v1_api_client.'
                              'read_namespaced_%s_scale' % snake_case_kind)
            response = read_scale_api(name=name, namespace=namespace)
        except Exception as e:
            error_reason = _("Failed the request to read a scale information."
                             " namespace: {namespace}, name: {name},"
                             " kind: {kind}, Reason: {exception}").format(
                namespace=namespace, name=name, kind=kind, exception=e)
            raise vnfm.CNFScaleFailed(reason=error_reason)

        return response

    def _call_patch_scale_api(self, app_v1_api_client, namespace, name,
                              kind, body):
        """select kubernetes patch scale api and call"""
        def convert(name):
            name_with_underscores = re.sub(
                '(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2',
                        name_with_underscores).lower()
        snake_case_kind = convert(kind)
        try:
            patch_scale_api = eval('app_v1_api_client.'
                              'patch_namespaced_%s_scale' % snake_case_kind)
            response = patch_scale_api(name=name, namespace=namespace,
                                       body=body)
        except Exception as e:
            error_reason = _("Failed the request to update a scale information"
                             ". namespace: {namespace}, name: {name},"
                             " kind: {kind}, Reason: {exception}").format(
                namespace=namespace, name=name, kind=kind, exception=e)
            raise vnfm.CNFScaleFailed(reason=error_reason)

        return response

    def _helm_scale(self, context, vnf_instance, policy):
        aspect_id = policy['name']
        vdu_defs = policy['vdu_defs']
        inst_additional_params = (vnf_instance.instantiated_vnf_info
                                  .additional_params)
        namespace = vnf_instance.vnf_metadata['namespace']
        helm_install_params = inst_additional_params.get(
            'using_helm_install_param', [])
        # Get releasename and chartname from Helm install params in Instantiate
        # request parameter by using vdu_mapping.
        vdu_mapping = inst_additional_params.get('vdu_mapping')
        for vdu_id, vdu_def in vdu_defs.items():
            release_name = (vdu_mapping.get(vdu_id, {}).get('helmreleasename'))
            if not release_name:
                continue
            helm_install_param = [
                param for param in helm_install_params
                if param.get('helmreleasename') == release_name]
            if not helm_install_param:
                error_reason = (f"Appropriate parameter for {aspect_id} is "
                                "not found in using_helm_install_param")
                LOG.error(error_reason)
                raise vnfm.CNFScaleFailed(reason=error_reason)
            if self._is_exthelmchart(helm_install_param[0]):
                chart_name = helm_install_param[0].get('helmchartname')
                upgrade_chart_name = "/".join(
                    [helm_install_param[0].get('helmrepositoryname'),
                     chart_name])
            else:
                chartfile_path = helm_install_param[0].get(
                    'helmchartfile_path')
                chartfile_name = chartfile_path[
                    chartfile_path.rfind(os.sep) + 1:]
                chart_name = "-".join(chartfile_name.split("-")[:-1])
                upgrade_chart_name = ("/var/tacker/helm/"
                                      f"{vnf_instance.id}/{chart_name}")
            vdu_properties = vdu_def.get('properties')
            break

        # Prepare for scale operation
        helm_replica_values = inst_additional_params.get('helm_replica_values')
        replica_param = helm_replica_values.get(aspect_id)
        vim_info = vnflcm_utils._get_vim(context,
            vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)
        ips, username, password = self._get_helm_info(vim_connection_info)
        # initialize HelmClient
        helmclient = helm_client.HelmClient(ips[0], username, password)
        # execute `helm get values` command to get current replicas
        current_replicas = helmclient.get_value(
            release_name, namespace, value=replica_param)
        vdu_profile = vdu_properties.get('vdu_profile')
        if policy['action'] == 'out':
            scale_replicas = current_replicas + policy['delta_num']
        elif policy['action'] == 'in':
            scale_replicas = current_replicas - policy['delta_num']
        # check if replica count is in min and man range defined in VNFD
        max_replicas = vdu_profile.get('max_number_of_instances')
        min_replicas = vdu_profile.get('min_number_of_instances')
        if (scale_replicas < min_replicas) or (scale_replicas > max_replicas):
            error_reason = ("The number of target replicas after"
                            f" scaling [{scale_replicas}] is out of range")
            LOG.error(error_reason)
            raise vnfm.CNFScaleFailed(reason=error_reason)

        # execute scale processing (`helm upgrade` command)
        upgrade_values = {replica_param: scale_replicas}
        helmclient.upgrade_values(release_name, upgrade_chart_name,
                                  namespace, parameters=upgrade_values)
        helmclient.close_session()

        return

    def _get_scale_target_info(self, aspect_id, vdu_defs, vnf_resources,
                               vdu_mapping):
        """get information of scale target."""
        if not vdu_mapping:
            is_found = False
            target_kinds = ["Deployment", "ReplicaSet", "StatefulSet"]
            for vnf_resource in vnf_resources:
                # The resource that matches the following is the
                # resource to be scaled:
                # The `name` of the resource stored in vnf_resource
                # (the name defined in `metadata.name` of Kubernetes
                # object file) matches the value of `properties.name`
                # of VDU defined in VNFD.
                # Infomation are stored in vnfc_resource as follows:
                #   - resource_name : "name"
                #   - resource_type : "api_version,kind"
                name = vnf_resource.resource_name
                for vdu_id, vdu_def in vdu_defs.items():
                    vdu_properties = vdu_def.get('properties')
                    if name == vdu_properties.get('name'):
                        _, kind = (vnf_resource.resource_type
                                   .split(COMMA_CHARACTER))
                        if kind in target_kinds:
                            is_found = True
                            break
                if is_found:
                    break
            else:
                error_reason = (
                    "Target VnfResource for aspectId"
                    f" {aspect_id} is not found in DB")
                raise vnfm.CNFScaleFailed(reason=error_reason)
        else:
            # Get parameters from vdu_mapping with using vdu_id as key.
            for vdu_id, vdu_def in vdu_defs.items():
                vdu_map_value = vdu_mapping.get(vdu_id, {})
                kind = vdu_map_value.get('kind')
                name = vdu_map_value.get('name')
                if kind and name:
                    vdu_properties = vdu_def.get('properties')
                    break
            else:
                error_reason = (
                    "Target vdu information for aspectId"
                    f" {aspect_id} is not found in vdu_mapping")
                raise vnfm.CNFScaleFailed(reason=error_reason)
        return kind, name, vdu_id, vdu_properties

    @log.log
    def scale(self, context, plugin, auth_attr, policy, region_name):
        """Scale function

        Scaling VNF is implemented by updating replicas through Kubernetes API.
        The min_replicas and max_replicas is limited by the number of replicas
        of policy scaling when user define VNF descriptor.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        try:
            vnf_instance = objects.VnfInstance.get_by_id(
                context, policy['vnf_instance_id'])
            # check use_helm flag
            inst_vnf_info = vnf_instance.instantiated_vnf_info
            additional_params = inst_vnf_info.additional_params
            if self._is_use_helm_flag(additional_params):
                self._helm_scale(context, vnf_instance, policy)
                return
            namespace = vnf_instance.vnf_metadata['namespace']
            vnf_resources = objects.VnfResourceList.get_by_vnf_instance_id(
                context, policy['vnf_instance_id'])
            app_v1_api_client = self.kubernetes.get_app_v1_api_client(
                auth=auth_cred)
            aspect_id = policy['name']
            vdu_defs = policy['vdu_defs']
            vdu_mapping = additional_params.get('vdu_mapping')
            kind, name, _, vdu_properties = self._get_scale_target_info(
                aspect_id, vdu_defs, vnf_resources, vdu_mapping)

            scale_info = self._call_read_scale_api(
                app_v1_api_client=app_v1_api_client,
                namespace=namespace,
                name=name,
                kind=kind)

            current_replicas = scale_info.status.replicas
            vdu_profile = vdu_properties.get('vdu_profile')
            if policy['action'] == 'out':
                scale_replicas = current_replicas + policy['delta_num']
            elif policy['action'] == 'in':
                scale_replicas = current_replicas - policy['delta_num']

            max_replicas = vdu_profile.get('max_number_of_instances')
            min_replicas = vdu_profile.get('min_number_of_instances')
            if (scale_replicas < min_replicas) or \
                    (scale_replicas > max_replicas):
                error_reason = (
                    "The number of target replicas after"
                    " scaling [{after_replicas}] is out of range").\
                    format(
                        after_replicas=scale_replicas)
                raise vnfm.CNFScaleFailed(reason=error_reason)

            scale_info.spec.replicas = scale_replicas
            self._call_patch_scale_api(
                app_v1_api_client=app_v1_api_client,
                namespace=namespace,
                name=name,
                kind=kind,
                body=scale_info)
        except Exception as e:
            LOG.error('Scaling VNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def is_match_pod_naming_rule(self, rsc_kind, rsc_name, pod_name):
        match_result = None
        if rsc_kind == 'Pod':
            # Expected example: name
            if rsc_name == pod_name:
                match_result = True
        elif rsc_kind == 'Deployment':
            # Expected example: name-012789abef-019az
            # NOTE(horie): The naming rule of Pod in deployment is
            # "(deployment name)-(pod template hash)-(5 charactors)".
            # The "pod template hash" string is generated from 32 bit hash.
            # This may be from 1 to 10 caracters but not sure the lower limit
            # from the source code of Kubernetes.
            match_result = re.match(
                rsc_name + '-([0-9a-f]{1,10})-([0-9a-z]{5})+$',
                pod_name)
        elif rsc_kind == 'ReplicaSet' or rsc_kind == 'DaemonSet':
            # Expected example: name-019az
            match_result = re.match(
                rsc_name + '-([0-9a-z]{5})+$',
                pod_name)
        elif rsc_kind == 'StatefulSet':
            # Expected example: name-0
            match_result = re.match(
                rsc_name + '-[0-9]+$',
                pod_name)
        if match_result:
            return True
        else:
            return False

    def scale_wait(self, context, plugin, auth_attr, policy, region_name,
                   last_event_id):
        """Scale wait function

        Scale wait function will marked VNF is ACTIVE when all status state
        from Pod objects is RUNNING.
        """
        # initialize Kubernetes APIs
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        try:
            vnf_instance = objects.VnfInstance.get_by_id(
                context, policy['vnf_instance_id'])
            namespace = vnf_instance.vnf_metadata['namespace']
            vnf_resources = objects.VnfResourceList.get_by_vnf_instance_id(
                context, policy['vnf_instance_id'])
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            app_v1_api_client = self.kubernetes.get_app_v1_api_client(
                auth=auth_cred)
            aspect_id = policy['name']
            vdu_defs = policy['vdu_defs']
            inst_vnf_info = vnf_instance.instantiated_vnf_info
            additional_params = inst_vnf_info.additional_params
            vdu_mapping = additional_params.get('vdu_mapping')
            kind, name, _, _ = self._get_scale_target_info(
                aspect_id, vdu_defs, vnf_resources, vdu_mapping)

            scale_info = self._call_read_scale_api(
                app_v1_api_client=app_v1_api_client,
                namespace=namespace,
                name=name,
                kind=kind)
            status = 'Pending'
            stack_retries = self.STACK_RETRIES
            error_reason = None
            while status == 'Pending' and stack_retries > 0:
                pods_information = list()
                respone = core_v1_api_client.list_namespaced_pod(
                    namespace=namespace)
                for pod in respone.items:
                    match_result = self.is_match_pod_naming_rule(
                        kind, name, pod.metadata.name)
                    if match_result:
                        pods_information.append(pod)

                status = self.get_pod_status(pods_information)
                if status == 'Running' and \
                        scale_info.spec.replicas != len(pods_information):
                    status = 'Pending'

                if status == 'Pending':
                    stack_retries = stack_retries - 1
                    time.sleep(self.STACK_RETRY_WAIT)
                elif status == 'Unknown':
                    error_reason = (
                        "CNF Scale failed caused by the Pod status"
                        " is Unknown")
                    raise vnfm.CNFScaleWaitFailed(reason=error_reason)

            if stack_retries == 0 and status != 'Running':
                error_reason = (
                    "CNF Scale failed to complete within"
                    " {wait} seconds while waiting for the aspect_id"
                    " {aspect_id} to be scaled").format(
                    wait=(self.STACK_RETRIES * self.STACK_RETRY_WAIT),
                    aspect_id=aspect_id)
                LOG.error("CNF Scale failed: %(reason)s",
                        {'reason': error_reason})
                raise vnfm.CNFScaleWaitFailed(reason=error_reason)
        except Exception as e:
            LOG.error('Scaling wait CNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    @log.log
    def get_resource_info(self, plugin, context, vnf_info, auth_attr,
                          region_name=None):
        # TODO(phuoc): will update it for other components
        pass

    def get_auth_creds(self, auth_cred):
        file_descriptor = self._create_ssl_ca_file(auth_cred)
        if ('username' not in auth_cred) and ('password' not in auth_cred):
            auth_cred['username'] = 'None'
            auth_cred['password'] = None
        return auth_cred, file_descriptor

    def _create_ssl_ca_file(self, auth_attr):
        ca_cert = utils.none_from_string(auth_attr.get('ssl_ca_cert'))
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

    def _is_use_helm_flag(self, additional_params):
        if not additional_params:
            return False
        use_helm = additional_params.get('use_helm')
        if type(use_helm) == str:
            return use_helm.lower() == 'true'
        return bool(use_helm)

    def _is_exthelmchart(self, helm_install_params):
        exthelmchart = helm_install_params.get('exthelmchart')
        if type(exthelmchart) == str:
            return exthelmchart.lower() == 'true'
        return bool(exthelmchart)

    def _validate_vdu_id_in_vdu_mapping(self, vdu_mapping, vnfd):
        """validate vdu_id between vdu_mapping and VDU defined in VNFD."""
        nodes = vnfd.get("topology_template", {}).get("node_templates", {})
        vdu_ids = {name for name, data in nodes.items()
                   if data['type'] == 'tosca.nodes.nfv.Vdu.Compute'}
        unfound_vdu_ids = {vdu_id for vdu_id in vdu_ids
                           if vdu_id not in vdu_mapping.keys()}
        if unfound_vdu_ids:
            error_reason = ("Parameter input values missing "
                            f"'vdu_id={str(unfound_vdu_ids)}' in vdu_mapping")
            LOG.error(error_reason)
            raise exceptions.InvalidInput(error_reason)

    def _validate_k8s_rsc_in_vdu_mapping(self, vdu_mapping, kind, name):
        """validate k8s resource kind/name between vdu_mapping and manifest."""
        if kind in ('Pod', 'Deployment', 'DaemonSet', 'StatefulSet',
                    'ReplicaSet'):
            found_rsc = {values['name'] for values in vdu_mapping.values()
                         if values['kind'] == kind and values['name'] == name}
            if not found_rsc:
                error_reason = ("Parameter input values missing resource info "
                                f"'{kind}:{name}' in vdu_mapping")
                LOG.error(error_reason)
                raise exceptions.InvalidInput(error_reason)

    def _pre_helm_install(self, context, vnf_instance, vim_connection_info,
                          instantiate_vnf_req, vnf_package_path):
        def _check_param_exists(params_dict, check_param):
            if check_param not in params_dict.keys():
                LOG.error("{check_param} is not found".format(
                    check_param=check_param))
                raise exceptions.InvalidInput(missing_key_err_msg %
                                              {"key": check_param})

        missing_key_err_msg = ("Parameter input values missing for"
                               " the key '%(key)s'")
        # check helm info in vim_connection_info
        if 'helm_info' not in vim_connection_info.extra.keys():
            reason = "helm_info is missing in vim_connection_info.extra."
            LOG.error(reason)
            raise vnfm.InvalidVimConnectionInfo(reason=reason)
        ips, username, password = self._get_helm_info(vim_connection_info)
        if not (ips and username and password):
            reason = "content of helm_info is invalid."
            LOG.error(reason)
            raise vnfm.InvalidVimConnectionInfo(reason=reason)

        # check helm install params
        additional_params = instantiate_vnf_req.additional_params
        _check_param_exists(additional_params, 'using_helm_install_param')
        helm_install_param_list = additional_params.get(
            'using_helm_install_param', [])
        if not helm_install_param_list:
            LOG.error("using_helm_install_param is empty.")
            raise exceptions.InvalidInput(missing_key_err_msg %
                                          {"key": "using_helm_install_param"})
        for helm_install_params in helm_install_param_list:
            # common parameter check
            _check_param_exists(helm_install_params, 'exthelmchart')
            _check_param_exists(helm_install_params, 'helmreleasename')
            if self._is_exthelmchart(helm_install_params):
                # parameter check (case: external helm chart)
                _check_param_exists(helm_install_params, 'helmchartname')
                _check_param_exists(helm_install_params, 'exthelmrepo_url')
                _check_param_exists(helm_install_params, 'helmrepositoryname')
            else:
                # parameter check (case: local helm chart)
                _check_param_exists(helm_install_params, 'helmchartfile_path')
                chartfile_path = helm_install_params.get('helmchartfile_path')
                abs_helm_chart_path = os.path.join(
                    vnf_package_path, chartfile_path)
                if not os.path.exists(abs_helm_chart_path):
                    LOG.error('Helm chart file {path} is not found.'.format(
                        path=chartfile_path))
                    raise vnfm.CnfDefinitionNotFound(path=chartfile_path)

        # check parameters for scale operation
        vnfd = vnflcm_utils.get_vnfd_dict(context, vnf_instance.vnfd_id,
                                          instantiate_vnf_req.flavour_id)
        tosca = tosca_template.ToscaTemplate(
            parsed_params={}, a_file=False, yaml_dict_tpl=vnfd,
            local_defs=toscautils.tosca_tmpl_local_defs())
        extract_policy_infos = vnflcm_utils.get_extract_policy_infos(tosca)
        helm_replica_values = additional_params.get('helm_replica_values', {})
        for aspect_id in extract_policy_infos['aspect_id_dict'].keys():
            if aspect_id not in helm_replica_values.keys():
                raise exceptions.InvalidInput(
                    f"Replica value for aspectId '{aspect_id}' is missing")

        # check vdu_mapping parameter
        _check_param_exists(additional_params, 'vdu_mapping')
        vdu_mapping = additional_params.get('vdu_mapping', {})
        # check vdu_id between vdu_mapping and VNFD
        self._validate_vdu_id_in_vdu_mapping(vdu_mapping, vnfd)
        # check helmreleasename in vdu_mapping and using_helm_install_param
        helmreleasenames = {values.get('helmreleasename')
                            for _, values in vdu_mapping.items()}
        for helm_install_param in helm_install_param_list:
            helmreleasename = helm_install_param.get('helmreleasename')
            if helmreleasename not in helmreleasenames:
                error_reason = ("Parameter input values missing "
                    f"'helmreleasename={helmreleasename}' in vdu_mapping")
                LOG.error(error_reason)
                raise exceptions.InvalidInput(error_reason)

    def _get_target_k8s_files(self, instantiate_vnf_req):
        if instantiate_vnf_req.additional_params and\
                CNF_TARGET_FILES_KEY in\
                instantiate_vnf_req.additional_params.keys():
            target_k8s_files = instantiate_vnf_req.\
                additional_params['lcm-kubernetes-def-files']
        else:
            target_k8s_files = list()
        return target_k8s_files

    def _create_vnf_resource(self, context, vnf_instance, file_content_dict):
        vnf_resource = vnf_resource_obj.VnfResource(
            context=context)
        vnf_resource.vnf_instance_id = vnf_instance.id
        metadata = file_content_dict.get('metadata', {})
        vnf_resource.resource_name = metadata.get('name', ' ')
        vnf_resource.resource_type = ','.join([
            file_content_dict.get('apiVersion', ''),
            file_content_dict.get('kind', '')])
        vnf_resource.resource_identifier = ''
        vnf_resource.resource_status = ''
        vnf_resource.tenant_id = vnf_instance.tenant_id
        return vnf_resource

    def pre_instantiation_vnf(self, context, vnf_instance,
                          vim_connection_info, vnf_software_images,
                          instantiate_vnf_req, vnf_package_path):
        # check use_helm flag
        if self._is_use_helm_flag(instantiate_vnf_req.additional_params):
            # parameter check
            self._pre_helm_install(context, vnf_instance, vim_connection_info,
                                   instantiate_vnf_req, vnf_package_path)
            # NOTE: In case of using helm, vnf_resources is created
            #       after `helm install` command is executed.

            namespace = (instantiate_vnf_req.additional_params
                         .get('namespace', ''))
            if not namespace:
                namespace = 'default'
            if not vnf_instance.vnf_metadata:
                vnf_instance.vnf_metadata = {}
            vnf_instance.vnf_metadata['namespace'] = namespace
            vnf_instance.vnf_metadata['tenant'] = namespace
            vnf_instance.save()

            return {}

        vnf_resources = dict()
        target_k8s_files = self._get_target_k8s_files(instantiate_vnf_req)
        if not target_k8s_files:
            # if artifact_files is not provided in request,
            # we consider k8s info in provided by TOSCA-based VNFD
            # and we will push the request to existed code
            return vnf_resources
        else:
            package_vnfd = vnfd_obj.VnfPackageVnfd.get_by_id(
                context, vnf_instance.vnfd_id)
            package_uuid = package_vnfd.package_uuid
            vnf_package = vnf_package_obj.VnfPackage.get_by_id(
                context, package_uuid, expected_attrs=['vnf_artifacts'])
            if vnf_package.vnf_artifacts:
                vnf_artifacts = vnf_package.vnf_artifacts
                length = len(vnf_artifacts)
                for target_k8s_file in target_k8s_files:
                    for index, vnf_artifact in enumerate(vnf_artifacts):
                        if vnf_artifact.artifact_path == target_k8s_file:
                            break
                        if length > 1 and index < length - 1:
                            continue
                        LOG.debug('CNF Artifact {path} is not found.'.format(
                            path=target_k8s_file))
                        setattr(vnf_instance, 'vim_connection_info', [])
                        setattr(vnf_instance, 'task_state', None)
                        vnf_instance.save()
                        raise vnfm.CnfDefinitionNotFound(
                            path=target_k8s_file)
            else:
                LOG.debug('VNF Artifact {path} is not found.'.format(
                    path=vnf_package.vnf_artifacts))
                setattr(vnf_instance, 'vim_connection_info', [])
                setattr(vnf_instance, 'task_state', None)
                vnf_instance.save()
                raise exceptions.VnfArtifactNotFound(id=vnf_package.id)

            chk_namespaces = []

            for target_k8s_index, target_k8s_file \
                    in enumerate(target_k8s_files):
                if ((urlparse(target_k8s_file).scheme == 'file') or
                        (bool(urlparse(target_k8s_file).scheme) and
                         bool(urlparse(target_k8s_file).netloc))):
                    file_content = urllib2.urlopen(target_k8s_file).read()
                else:
                    target_k8s_file_path = os.path.join(
                        vnf_package_path, target_k8s_file)
                    with open(target_k8s_file_path, 'r') as f:
                        file_content = f.read()
                file_content_dict_list = yaml.safe_load_all(file_content)
                vnf_resources_temp = []
                for file_content_dict in file_content_dict_list:
                    vnf_resource = self._create_vnf_resource(
                        context, vnf_instance, file_content_dict)
                    vnf_resources_temp.append(vnf_resource)

                    metadata = file_content_dict.get('metadata', {})
                    chk_namespaces.append(
                        {'namespace': metadata.get('namespace', ''),
                         'kind': file_content_dict.get('kind', '')})

                vnf_resources[target_k8s_index] = vnf_resources_temp

            # check vdu_mapping parameter if exist
            vdu_mapping = (instantiate_vnf_req.additional_params
                           .get('vdu_mapping'))
            if vdu_mapping:
                vnfd = vnflcm_utils.get_vnfd_dict(context,
                    vnf_instance.vnfd_id, instantiate_vnf_req.flavour_id)
                # check vdu_id between vdu_mapping and VNFD
                self._validate_vdu_id_in_vdu_mapping(vdu_mapping, vnfd)
                for resources in vnf_resources.values():
                    for vnf_resource in resources:
                        name = vnf_resource.resource_name
                        _, kind = vnf_resource.resource_type.split(
                            COMMA_CHARACTER)
                        # check kind and name between vdu_mapping and manifest
                        self._validate_k8s_rsc_in_vdu_mapping(
                            vdu_mapping, kind, name)

            LOG.debug(f"all manifest namespace and kind: {chk_namespaces}")
            k8s_utils.check_and_save_namespace(
                instantiate_vnf_req, chk_namespaces, vnf_instance)

            return vnf_resources

    def delete_vnf_instance_resource(self, context, vnf_instance,
            vim_connection_info, vnf_resource):
        pass

    def _helm_install(self, context, vnf_instance, vim_connection_info,
                      instantiate_vnf_req, vnf_package_path, transformer):
        additional_params = instantiate_vnf_req.additional_params
        namespace = vnf_instance.vnf_metadata['namespace']
        helm_inst_param_list = additional_params.get(
            'using_helm_install_param')
        ips, username, password = self._get_helm_info(vim_connection_info)
        vnf_resources = []
        k8s_objs = []
        for ip_idx, ip in enumerate(ips):
            # initialize HelmClient
            helmclient = helm_client.HelmClient(ip, username, password)
            for inst_params in helm_inst_param_list:
                release_name = inst_params.get('helmreleasename')
                parameters = inst_params.get('helmparameter')
                if self._is_exthelmchart(inst_params):
                    # prepare using external helm chart
                    chart_name = inst_params.get('helmchartname')
                    repo_url = inst_params.get('exthelmrepo_url')
                    repo_name = inst_params.get('helmrepositoryname')
                    # execute `helm repo add` command
                    helmclient.add_repository(repo_name, repo_url)
                    install_chart_name = '/'.join([repo_name, chart_name])
                else:
                    # prepare using local helm chart
                    chartfile_path = inst_params.get('helmchartfile_path')
                    src_path = os.path.join(vnf_package_path, chartfile_path)
                    dst_dir = os.path.join(
                        HELM_CHART_DIR_BASE, vnf_instance.id)
                    # put helm chart file to Kubernetes controller node
                    helmclient.put_helmchart(src_path, dst_dir)
                    chart_file_name = src_path[src_path.rfind(os.sep) + 1:]
                    chart_name = "-".join(chart_file_name.split("-")[:-1])
                    install_chart_name = os.path.join(dst_dir, chart_name)
                if ip_idx == 0:
                    # execute `helm install` command
                    helmclient.install(release_name, install_chart_name,
                                       namespace, parameters)
                    # get manifest by using `helm get manifest` command
                    mf_content = helmclient.get_manifest(
                        release_name, namespace)
                    k8s_objs_tmp = transformer.get_k8s_objs_from_manifest(
                        mf_content, namespace)
                    for k8s_obj in k8s_objs_tmp:
                        # set status in k8s_obj to 'Creating'
                        k8s_obj['status'] = 'Creating'
                    k8s_objs.extend(k8s_objs_tmp)
                    mf_content_dicts = list(yaml.safe_load_all(mf_content))
                    for mf_content_dict in mf_content_dicts:
                        vnf_resource = self._create_vnf_resource(
                            context, vnf_instance, mf_content_dict)
                        vnf_resources.append(vnf_resource)
            helmclient.close_session()
        # save the vnf resources in the db
        for vnf_resource in vnf_resources:
            vnf_resource.create()
        return k8s_objs

    def instantiate_vnf(self, context, vnf_instance, vnfd_dict,
                        vim_connection_info, instantiate_vnf_req,
                        grant_response, vnf_package_path,
                        plugin=None):
        target_k8s_files = self._get_target_k8s_files(instantiate_vnf_req)
        namespace = vnf_instance.vnf_metadata['namespace']
        auth_attr = vim_connection_info.access_info
        use_helm_flag = self._is_use_helm_flag(
            instantiate_vnf_req.additional_params)
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        k8s_client_dict = self.kubernetes.get_k8s_client_dict(auth_cred)
        transformer = translate_outputs.Transformer(
            None, None, None, k8s_client_dict)
        deployment_dict_list = list()
        if use_helm_flag:
            k8s_objs = self._helm_install(
                context, vnf_instance, vim_connection_info,
                instantiate_vnf_req, vnf_package_path, transformer)
        else:
            k8s_objs = transformer.get_k8s_objs_from_yaml(
                target_k8s_files, vnf_package_path, namespace)
            k8s_objs = transformer.deploy_k8s(k8s_objs)
        vnfd_dict['current_error_point'] = EP.POST_VIM_CONTROL
        k8s_objs = self.create_wait_k8s(
            k8s_objs, k8s_client_dict, vnf_instance)
        for k8s_obj in k8s_objs:
            deployment_dict = dict()
            deployment_dict['namespace'] = k8s_obj.get('namespace')
            if k8s_obj.get('object').metadata:
                deployment_dict['name'] = k8s_obj.get('object').\
                    metadata.name
            else:
                deployment_dict['name'] = ''
            deployment_dict['apiVersion'] = k8s_obj.get(
                'object').api_version
            deployment_dict['kind'] = k8s_obj.get('object').kind
            deployment_dict['status'] = k8s_obj.get('status')
            deployment_dict_list.append(deployment_dict)
        deployment_str_list = [str(x) for x in deployment_dict_list]
        # all the deployment object will store into resource_info_str.
        # and the instance_id is created from all deployment_dict.
        resource_info_str = ';'.join(deployment_str_list)
        self.clean_authenticate_vim(auth_cred, file_descriptor)
        vnfd_dict['instance_id'] = resource_info_str
        return resource_info_str

    def _post_helm_install(self, context, vim_connection_info,
                           instantiate_vnf_req, transformer, namespace):
        additional_params = instantiate_vnf_req.additional_params
        helm_inst_param_list = additional_params.get(
            'using_helm_install_param')
        ips, username, password = self._get_helm_info(vim_connection_info)
        k8s_objs = []
        # initialize HelmClient
        helmclient = helm_client.HelmClient(ips[0], username, password)
        for helm_inst_params in helm_inst_param_list:
            release_name = helm_inst_params.get('helmreleasename')
            # get manifest by using `helm get manifest` command
            mf_content = helmclient.get_manifest(release_name, namespace)
            k8s_objs_tmp = transformer.get_k8s_objs_from_manifest(
                mf_content, namespace)
            k8s_objs.extend(k8s_objs_tmp)
        helmclient.close_session()
        return k8s_objs

    def post_vnf_instantiation(self, context, vnf_instance,
                               vim_connection_info, instantiate_vnf_req):
        """Initially store VnfcResourceInfo after instantiation

        After instantiation, this function gets pods information from
        Kubernetes VIM and store information such as pod name and resource kind
        and metadata, and vdu id.
        """
        auth_attr = vim_connection_info.access_info
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        namespace = vnf_instance.vnf_metadata['namespace']
        try:
            # get Kubernetes object files
            target_k8s_files = self._get_target_k8s_files(instantiate_vnf_req)
            vnf_package_path = vnflcm_utils._get_vnf_package_path(
                context, vnf_instance.vnfd_id)
            # initialize Transformer
            transformer = translate_outputs.Transformer(
                None, None, None, None)
            additional_params = instantiate_vnf_req.additional_params
            if self._is_use_helm_flag(additional_params):
                k8s_objs = self._post_helm_install(context,
                    vim_connection_info, instantiate_vnf_req, transformer,
                    namespace)
            else:
                # get Kubernetes object
                k8s_objs = transformer.get_k8s_objs_from_yaml(
                    target_k8s_files, vnf_package_path, namespace)
            vdu_mapping = additional_params.get('vdu_mapping')
            if not vdu_mapping:
                # get TOSCA node templates
                vnfd_dict = vnflcm_utils._get_vnfd_dict(
                    context, vnf_instance.vnfd_id,
                    vnf_instance.instantiated_vnf_info.flavour_id)
                tosca = tosca_template.ToscaTemplate(
                    parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict,
                    local_defs=toscautils.tosca_tmpl_local_defs())
                tosca_node_tpls = tosca.topology_template.nodetemplates
                # get vdu_ids dict {vdu_name: vdu_id} from VNFD
                vdu_ids = {}
                for node_tpl in tosca_node_tpls:
                    for node_name, node_value in node_tpl.templates.items():
                        if (node_value.get('type') ==
                                "tosca.nodes.nfv.Vdu.Compute"):
                            vdu_id = node_name
                            vdu_name = node_value.get('properties').get('name')
                            vdu_ids[vdu_name] = vdu_id
            else:
                # get vdu_ids dict {vdu_name: vdu_id} from vdu_mapping
                vdu_ids = {values.get('name'): vdu_id
                           for vdu_id, values in vdu_mapping.items()}
            # initialize Kubernetes APIs
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            target_kinds = ["Pod", "Deployment", "DaemonSet", "StatefulSet",
                            "ReplicaSet"]
            pod_list_dict = {}
            vnfc_resource_list = []
            for k8s_obj in k8s_objs:
                rsc_kind = k8s_obj.get('object').kind
                if rsc_kind not in target_kinds:
                    # Skip if rsc_kind is not target kind
                    continue
                rsc_name = k8s_obj.get('object').metadata.name
                # get V1PodList by namespace
                if namespace in pod_list_dict.keys():
                    pod_list = pod_list_dict.get(namespace)
                else:
                    pod_list = core_v1_api_client.list_namespaced_pod(
                        namespace=namespace)
                    pod_list_dict[namespace] = pod_list
                # get initially store VnfcResourceInfo after instantiation
                for pod in pod_list.items:
                    pod_name = pod.metadata.name
                    match_result = self.is_match_pod_naming_rule(
                        rsc_kind, rsc_name, pod_name)
                    if match_result:
                        # get metadata
                        metadata = {}
                        metadata[rsc_kind] = jsonutils.dumps(
                            k8s_obj.get('object').metadata.to_dict())
                        if rsc_kind != 'Pod':
                            metadata['Pod'] = jsonutils.dumps(
                                k8s_obj.get('object').spec.template.metadata.
                                to_dict())
                        # generate VnfcResourceInfo
                        vnfc_resource = objects.VnfcResourceInfo()
                        vnfc_resource.id = uuidutils.generate_uuid()
                        vnfc_resource.vdu_id = vdu_ids.get(rsc_name)
                        resource = objects.ResourceHandle()
                        resource.resource_id = pod_name
                        resource.vim_level_resource_type = rsc_kind
                        vnfc_resource.compute_resource = resource
                        vnfc_resource.metadata = metadata
                        vnfc_resource_list.append(vnfc_resource)

            if vnfc_resource_list:
                inst_vnf_info = vnf_instance.instantiated_vnf_info
                inst_vnf_info.vnfc_resource_info = vnfc_resource_list
        except Exception as e:
            LOG.error('Update vnfc resource info got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def _get_vnfc_rscs_with_vnfc_id(self, inst_vnf_info, heal_vnf_request):
        if not heal_vnf_request.vnfc_instance_id:
            # include all vnfc resources
            return [resource for resource in inst_vnf_info.vnfc_resource_info]

        vnfc_resources = []
        for vnfc_resource in inst_vnf_info.vnfc_resource_info:
            if vnfc_resource.id in heal_vnf_request.vnfc_instance_id:
                vnfc_resources.append(vnfc_resource)
        return vnfc_resources

    def _get_added_pod_names(self, core_v1_api_client, inst_vnf_info, vdu_id,
                             vnfc_resource, pod_list_dict, namespace):
        compute_resource = vnfc_resource.compute_resource
        rsc_kind = compute_resource.vim_level_resource_type
        rsc_metadata = jsonutils.loads(
            vnfc_resource.metadata.get(rsc_kind))
        rsc_name = rsc_metadata.get('name')
        # Get pod list from kubernetes
        if namespace in pod_list_dict.keys():
            pod_list = pod_list_dict.get(namespace)
        else:
            pod_list = core_v1_api_client.list_namespaced_pod(
                namespace=namespace)
            pod_list_dict[namespace] = pod_list
        # Sort by newest creation_timestamp
        sorted_pod_list = sorted(pod_list.items, key=lambda x:
            x.metadata.creation_timestamp, reverse=True)
        # Get the associated pod name that runs with the actual kubernetes
        actual_pod_names = list()
        for pod in sorted_pod_list:
            match_result = self.is_match_pod_naming_rule(
                rsc_kind, rsc_name, pod.metadata.name)
            if match_result:
                actual_pod_names.append(pod.metadata.name)
        # Get the associated pod name stored in vnfcResourceInfo
        stored_pod_names = []
        for vnfc_rsc_info in inst_vnf_info.vnfc_resource_info:
            if vnfc_rsc_info.vdu_id == vnfc_resource.vdu_id:
                stored_pod_names.append(
                    vnfc_rsc_info.compute_resource.resource_id)
        # Get the added pod name that does not exist in vnfcResourceInfo
        added_pod_names = [
            actl_pn for actl_pn in actual_pod_names
            if actl_pn not in stored_pod_names
        ]
        return actual_pod_names, added_pod_names

    def heal_vnf(self, context, vnf_instance, vim_connection_info,
                 heal_vnf_request):
        """Heal function

        This function heals vnfc instances (mapped as Pod),
        and update vnfcResourceInfo which are not the target of healing
        before healing operation.

        """
        # initialize Kubernetes APIs
        auth_attr = vim_connection_info.access_info
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        namespace = vnf_instance.vnf_metadata['namespace']
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            # get vnfc_resource_info list for healing
            vnfc_resources = self._get_vnfc_rscs_with_vnfc_id(
                inst_vnf_info=inst_vnf_info,
                heal_vnf_request=heal_vnf_request
            )
            # Updates resource_id in vnfc_resource_info which are not the
            # target of healing before heal operation because they may have
            # been re-created by kubelet of Kubernetes automatically and their
            # resource_id (as Pod name) have been already changed
            updated_vdu_ids = []
            pod_list_dict = {}
            for vnfc_resource in vnfc_resources:
                vdu_id = vnfc_resource.vdu_id
                if vdu_id in updated_vdu_ids:
                    # For updated vdu_id, go to the next Loop
                    continue
                actual_pod_names, added_pod_names = self._get_added_pod_names(
                    core_v1_api_client, inst_vnf_info, vdu_id, vnfc_resource,
                    pod_list_dict, namespace)

                if added_pod_names:
                    heal_target_ids = heal_vnf_request.vnfc_instance_id
                    for vnfc_rsc in inst_vnf_info.vnfc_resource_info:
                        stored_pod_name = vnfc_rsc.compute_resource.resource_id
                        # Updated vnfcResourceInfo of the same vdu_id other
                        # than heal target
                        if (vnfc_rsc.id not in heal_target_ids) and\
                                (vdu_id == vnfc_rsc.vdu_id) and\
                                (stored_pod_name not in actual_pod_names):
                            pod_name = added_pod_names.pop()
                            vnfc_rsc.compute_resource.resource_id = pod_name
                            LOG.warning("Update resource_id before healing,"
                                        " vnfc_resource_info.id:%(vnfc_id)s,"
                                        " pod_name:%(pod_name)s",
                                        {'vnfc_id': vnfc_rsc.id,
                                        'pod_name': pod_name})
                        if not added_pod_names:
                            break
                updated_vdu_ids.append(vdu_id)

            for vnfc_resource in vnfc_resources:
                body = client.V1DeleteOptions(propagation_policy='Foreground')
                compute_resource = vnfc_resource.compute_resource
                rsc_kind = compute_resource.vim_level_resource_type
                pod_name = compute_resource.resource_id
                rsc_metadata = jsonutils.loads(
                    vnfc_resource.metadata.get(rsc_kind))

                if rsc_kind == 'Pod':
                    rsc_name = rsc_metadata.get('name')
                    # Get pod information for re-creation before deletion
                    pod_info = core_v1_api_client.read_namespaced_pod(
                        namespace=namespace,
                        name=rsc_name
                    )
                    # Delete Pod
                    core_v1_api_client.delete_namespaced_pod(
                        namespace=namespace,
                        name=pod_name,
                        body=body
                    )
                    # Check and wait that the Pod is deleted
                    stack_retries = self.STACK_RETRIES
                    for cnt in range(self.STACK_RETRIES):
                        try:
                            core_v1_api_client.read_namespaced_pod(
                                namespace=namespace,
                                name=pod_name
                            )
                        except Exception as e:
                            if e.status == 404:
                                break
                            else:
                                error_reason = _("Failed the request to read a"
                                    " Pod information. namespace: {namespace},"
                                    " pod_name: {name}, kind: {kind}, Reason: "
                                    "{exception}").format(
                                        namespace=namespace, name=pod_name,
                                        kind=rsc_kind, exception=e)
                                raise vnfm.CNFHealFailed(reason=error_reason)
                        stack_retries = stack_retries - 1
                        time.sleep(self.STACK_RETRY_WAIT)

                    # Number of retries exceeded retry count
                    if stack_retries == 0:
                        error_reason = _("Resource healing is not completed"
                            "within {wait} seconds").format(wait=(
                                self.STACK_RETRIES * self.STACK_RETRY_WAIT))
                        LOG.error("CNF Healing failed: %(reason)s",
                                  {'reason': error_reason})
                        raise vnfm.CNFHealFailed(reason=error_reason)

                    # Recreate pod using retained pod_info
                    transformer = translate_outputs.Transformer(
                        None, None, None, None)
                    metadata = transformer.get_object_meta(rsc_metadata)
                    body = client.V1Pod(metadata=metadata, spec=pod_info.spec)
                    core_v1_api_client.create_namespaced_pod(
                        namespace=namespace,
                        body=body
                    )
                elif (rsc_kind in ['Deployment', 'DaemonSet', 'StatefulSet',
                                   'ReplicaSet']):
                    try:
                        # Delete Pod (Pod is automatically re-created)
                        core_v1_api_client.delete_namespaced_pod(
                            namespace=namespace,
                            name=pod_name,
                            body=body
                        )
                    except Exception as e:
                        if e.status == 404:
                            # If when the pod to be deleted does not exist,
                            # change resource_id to "POD_NOT_FOUND"
                            compute_resource = vnfc_resource.compute_resource
                            compute_resource.resource_id = VNFC_POD_NOT_FOUND
                            LOG.warning("Target pod to delete is not found,"
                                        " vnfc_resource_info.id:%(vnfc_id)s,"
                                        " pod_name:%(pod_name)s",
                                        {'vnfc_id': vnfc_resource.id,
                                        'pod_name': pod_name})
                        else:
                            error_reason = _("Failed the request to delete a "
                                "Pod. namespace: {namespace}, pod_name: {name}"
                                ", kind: {kind}, Reason: {exception}").format(
                                    namespace=namespace, name=pod_name,
                                    kind=rsc_kind, exception=e)
                            raise vnfm.CNFHealFailed(reason=error_reason)
                else:
                    error_reason = _(
                        "{vnfc_instance_id} is a kind of Kubertnetes"
                        " resource that is not covered").format(
                        vnfc_instance_id=vnfc_resource.id)
                    LOG.error("CNF Heal failed: %(reason)s",
                              {'reason': error_reason})
                    raise vnfm.CNFHealFailed(reason=error_reason)
        except Exception as e:
            LOG.error('Healing CNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def heal_vnf_wait(self, context, vnf_instance,
                      vim_connection_info, heal_vnf_request):
        """heal wait function

        Wait until all status from Pod objects is RUNNING.
        """
        # initialize Kubernetes APIs
        auth_attr = vim_connection_info.access_info
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        namespace = vnf_instance.vnf_metadata['namespace']
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            app_v1_api_client = self.kubernetes.get_app_v1_api_client(
                auth=auth_cred)
            vnfc_resources = self._get_vnfc_rscs_with_vnfc_id(
                inst_vnf_info=vnf_instance.instantiated_vnf_info,
                heal_vnf_request=heal_vnf_request)
            # Exclude entries where pods were not found when heal
            vnfc_resources = [rsc for rsc in vnfc_resources
                              if rsc.compute_resource.
                              resource_id != VNFC_POD_NOT_FOUND]

            if not vnfc_resources:
                # If heal is not running, wait is no need
                return

            # Get kubernetes resource information from target vnfcResourceInfo
            k8s_resources = list()
            for vnfc_resource in vnfc_resources:
                info = {}
                compute_resource = vnfc_resource.compute_resource
                info['kind'] = compute_resource.vim_level_resource_type
                rsc_metadata = jsonutils.loads(
                    vnfc_resource.metadata.get(info['kind']))
                info['name'] = rsc_metadata.get('name')
                info['namespace'] = namespace
                if not info['namespace']:
                    info['namespace'] = "default"
                k8s_resources.append(info)
            # exclude duplicate entries
            k8s_resources = list(map(jsonutils.loads,
                                 set(map(jsonutils.dumps, k8s_resources))))
            # get replicas of scalable resources for checking number of pod
            scalable_kinds = ["Deployment", "ReplicaSet", "StatefulSet"]
            for k8s_resource in k8s_resources:
                if k8s_resource.get('kind') in scalable_kinds:
                    scale_info = self._call_read_scale_api(
                        app_v1_api_client=app_v1_api_client,
                        namespace=k8s_resource.get('namespace'),
                        name=k8s_resource.get('name'),
                        kind=k8s_resource.get('kind'))
                    k8s_resource['replicas'] = scale_info.spec.replicas
            stack_retries = self.STACK_RETRIES
            status = 'Pending'
            while status == 'Pending' and stack_retries > 0:
                pods_information = []
                pod_list_dict = {}
                is_unmatch_pods_num = False
                # Get related pod information and check status
                for k8s_resource in k8s_resources:
                    namespace = k8s_resource.get('namespace')
                    if namespace in pod_list_dict.keys():
                        pod_list = pod_list_dict.get(namespace)
                    else:
                        pod_list = core_v1_api_client.list_namespaced_pod(
                            namespace=k8s_resource.get('namespace'))
                        pod_list_dict[namespace] = pod_list
                    tmp_pods_info = list()
                    for pod in pod_list.items:
                        match_result = self.is_match_pod_naming_rule(
                            k8s_resource.get('kind'),
                            k8s_resource.get('name'),
                            pod.metadata.name)
                        if match_result:
                            tmp_pods_info.append(pod)
                    # NOTE(ueha): The status of pod being deleted is retrieved
                    # as "Running", which cause incorrect information to be
                    # stored in vnfcResouceInfo. Therefore, for the scalable
                    # kinds, by comparing the actual number of pods with the
                    # replicas, it can wait until the pod deletion is complete
                    # and store correct information to vnfcResourceInfo.
                    if k8s_resource.get('kind') in scalable_kinds and \
                            k8s_resource.get('replicas') != len(tmp_pods_info):
                        LOG.warning("Unmatch number of pod. (kind: %(kind)s,"
                            " name: %(name)s, replicas: %(replicas)s,"
                            " actual_pod_num: %(actual_pod_num)s)", {
                                'kind': k8s_resource.get('kind'),
                                'name': k8s_resource.get('name'),
                                'replicas': str(k8s_resource.get('replicas')),
                                'actual_pod_num': str(len(tmp_pods_info))})
                        is_unmatch_pods_num = True
                    pods_information.extend(tmp_pods_info)
                status = self.get_pod_status(pods_information)

                if status == 'Unknown':
                    error_reason = _("Pod status is found Unknown")
                    LOG.error("CNF Healing failed: %(reason)s",
                              {'reason': error_reason})
                    raise vnfm.CNFHealWaitFailed(reason=error_reason)
                elif status == 'Pending' or is_unmatch_pods_num:
                    time.sleep(self.STACK_RETRY_WAIT)
                    stack_retries = stack_retries - 1
                    status = 'Pending'

            if stack_retries == 0 and status != 'Running':
                error_reason = _("Resource healing is not completed within"
                                " {wait} seconds").format(
                    wait=(self.STACK_RETRIES *
                        self.STACK_RETRY_WAIT))
                LOG.error("CNF Healing failed: %(reason)s",
                    {'reason': error_reason})
                raise vnfm.CNFHealWaitFailed(reason=error_reason)
        except Exception as e:
            LOG.error('Healing wait CNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def post_heal_vnf(self, context, vnf_instance, vim_connection_info,
                      heal_vnf_request):
        """Update VnfcResourceInfo after healing"""
        # initialize Kubernetes APIs
        auth_attr = vim_connection_info.access_info
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        namespace = vnf_instance.vnf_metadata['namespace']
        try:
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            vnfc_resources = self._get_vnfc_rscs_with_vnfc_id(
                inst_vnf_info=inst_vnf_info,
                heal_vnf_request=heal_vnf_request
            )
            # initialize
            updated_vdu_ids = []
            pod_list_dict = {}
            for vnfc_resource in vnfc_resources:
                vdu_id = vnfc_resource.vdu_id
                if vdu_id in updated_vdu_ids:
                    # For updated vdu_id, go to the next Loop
                    continue
                compute_resource = vnfc_resource.compute_resource
                rsc_kind = compute_resource.vim_level_resource_type
                pod_name = compute_resource.resource_id

                if rsc_kind == 'Pod' or rsc_kind == 'StatefulSet':
                    # No update required as the pod name does not change
                    continue

                # Update vnfcResourceInfo when other rsc_kind
                # (Deployment, DaemonSet, ReplicaSet)
                actual_pod_names, added_pod_names = self._get_added_pod_names(
                    core_v1_api_client, inst_vnf_info, vdu_id, vnfc_resource,
                    pod_list_dict, namespace)

                updated_vnfc_ids = []
                # Update entries that pod was not found when heal_vnf method
                if added_pod_names:
                    for vnfc_rsc in vnfc_resources:
                        rsc_id = vnfc_rsc.compute_resource.resource_id
                        if vdu_id == vnfc_rsc.vdu_id and \
                                rsc_id == VNFC_POD_NOT_FOUND:
                            pod_name = added_pod_names.pop()
                            vnfc_rsc.compute_resource.resource_id = pod_name
                            LOG.warning("Update resource_id of the"
                                        " entry where the pod was not found,"
                                        " vnfc_resource_info.id:%(vnfc_id)s,"
                                        " new podname:%(pod_name)s",
                                        {'vnfc_id': vnfc_rsc.id,
                                        'pod_name': pod_name})
                            updated_vnfc_ids.append(vnfc_rsc.id)
                        if not added_pod_names:
                            break
                # Update entries that was healed successful
                if added_pod_names:
                    for vnfc_rsc_id in heal_vnf_request.vnfc_instance_id:
                        if vnfc_rsc_id in updated_vnfc_ids:
                            # If the entry has already been updated,
                            # go to the next loop
                            continue
                        for vnfc_rsc in vnfc_resources:
                            if vdu_id == vnfc_rsc.vdu_id and \
                                    vnfc_rsc_id == vnfc_rsc.id:
                                pod_name = added_pod_names.pop()
                                compute_resource = vnfc_rsc.compute_resource
                                compute_resource.resource_id = pod_name
                            if not added_pod_names:
                                break
                updated_vdu_ids.append(vdu_id)
        except Exception as e:
            LOG.error('Post healing CNF got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def change_ext_conn_vnf(self, context, vnf_instance, vnf_dict,
                            vim_connection_info, change_ext_conn_req):
        raise NotImplementedError()

    def change_ext_conn_vnf_wait(self, context, vnf_instance,
                                 vim_connection_info):
        raise NotImplementedError()

    def post_change_ext_conn_vnf(self, context, vnf_instance,
                                 vim_connection_info):
        raise NotImplementedError()

    def get_scale_ids(self,
                      plugin,
                      context,
                      vnf_dict,
                      auth_attr,
                      region_name):
        return_id_list = []
        return return_id_list

    def get_scale_in_ids(self,
                         plugin,
                         context,
                         vnf_dict,
                         is_reverse,
                         auth_attr,
                         region_name,
                         number_of_steps):
        return_id_list = []
        return_name_list = []
        return_grp_id = None
        return_res_num = None
        return return_id_list, return_name_list, return_grp_id, return_res_num

    def scale_resource_update(self, context, vnf_instance,
                              scale_vnf_request, vnf_info,
                              vim_connection_info):
        """Update VnfcResourceInfo after scaling"""
        auth_attr = vim_connection_info.access_info
        auth_cred, file_descriptor = self.get_auth_creds(auth_attr)
        inst_vnf_info = vnf_instance.instantiated_vnf_info
        try:
            # initialize Kubernetes APIs
            core_v1_api_client = self.kubernetes.get_core_v1_api_client(
                auth=auth_cred)
            vnf_resources = objects.VnfResourceList.get_by_vnf_instance_id(
                context, vnf_instance.id)
            # get scale target informations
            vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
                vnf_instance.vnfd_id,
                inst_vnf_info.flavour_id)
            tosca = tosca_template.ToscaTemplate(
                parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict,
                local_defs=toscautils.tosca_tmpl_local_defs())
            extract_policy_infos = vnflcm_utils.get_extract_policy_infos(tosca)
            aspect_id = scale_vnf_request.aspect_id
            vdu_defs = vnflcm_utils.get_target_vdu_def_dict(
                extract_policy_infos=extract_policy_infos,
                aspect_id=aspect_id,
                tosca=tosca)
            namespace = vnf_instance.vnf_metadata['namespace']
            inst_vnf_info = vnf_instance.instantiated_vnf_info
            vdu_mapping = (inst_vnf_info.additional_params
                           .get('vdu_mapping'))
            rsc_kind, rsc_name, target_vdu_id, _ = self._get_scale_target_info(
                aspect_id, vdu_defs, vnf_resources, vdu_mapping)
            # extract stored Pod names by vdu_id
            stored_pod_list = []
            metadata = None
            for vnfc_resource in inst_vnf_info.vnfc_resource_info:
                if vnfc_resource.vdu_id == target_vdu_id:
                    stored_pod_list.append(
                        vnfc_resource.compute_resource.resource_id)
                    if not metadata:
                        # get metadata for new VnfcResourceInfo entry
                        metadata = vnfc_resource.metadata
            # get actual Pod name list
            pod_list = core_v1_api_client.list_namespaced_pod(
                namespace=namespace)
            actual_pod_list = []
            for pod in pod_list.items:
                match_result = self.is_match_pod_naming_rule(
                    rsc_kind, rsc_name, pod.metadata.name)
                if match_result:
                    actual_pod_list.append(pod.metadata.name)
            # Remove the reduced pods from VnfcResourceInfo
            del_index = []
            for index, vnfc in enumerate(inst_vnf_info.vnfc_resource_info):
                if vnfc.compute_resource.resource_id not in actual_pod_list \
                        and vnfc.vdu_id == target_vdu_id:
                    del_index.append(index)
            for ind in reversed(del_index):
                inst_vnf_info.vnfc_resource_info.pop(ind)
            # Add the increased pods to VnfcResourceInfo
            for actual_pod_name in actual_pod_list:
                if actual_pod_name not in stored_pod_list:
                    add_vnfc_resource = objects.VnfcResourceInfo()
                    add_vnfc_resource.id = uuidutils.generate_uuid()
                    add_vnfc_resource.vdu_id = target_vdu_id
                    resource = objects.ResourceHandle()
                    resource.resource_id = actual_pod_name
                    resource.vim_level_resource_type = rsc_kind
                    add_vnfc_resource.compute_resource = resource
                    add_vnfc_resource.metadata = metadata
                    inst_vnf_info.vnfc_resource_info.append(
                        add_vnfc_resource)
        except Exception as e:
            LOG.error('Update vnfc resource info got an error due to %s', e)
            raise
        finally:
            self.clean_authenticate_vim(auth_cred, file_descriptor)

    def scale_in_reverse(self,
              context,
              plugin,
              auth_attr,
              vnf_info,
              scale_vnf_request,
              region_name,
              scale_name_list,
              grp_id,
              vnf_instance):
        # NOTE(ueha): The `is_reverse` option is not supported in kubernetes
        # VIM, and returns an error response to the user if `is_reverse` is
        # true. However, since this method is called in the sequence of
        # rollback operation, implementation is required.
        vnf_instance_id = vnf_info['vnf_lcm_op_occ'].vnf_instance_id
        aspect_id = scale_vnf_request.aspect_id
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
            vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)
        tosca = tosca_template.ToscaTemplate(
            parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict,
            local_defs=toscautils.tosca_tmpl_local_defs())
        extract_policy_infos = vnflcm_utils.get_extract_policy_infos(tosca)

        policy = dict()
        policy['name'] = aspect_id
        policy['action'] = 'in'
        policy['vnf_instance_id'] = vnf_instance_id
        policy['vdu_defs'] = vnflcm_utils.get_target_vdu_def_dict(
            extract_policy_infos=extract_policy_infos,
            aspect_id=scale_vnf_request.aspect_id,
            tosca=tosca)
        policy['delta_num'] = vnflcm_utils.get_scale_delta_num(
            extract_policy_infos=extract_policy_infos,
            aspect_id=scale_vnf_request.aspect_id)

        self.scale(context, plugin, auth_attr, policy, region_name)

    def scale_out_initial(self,
              context,
              plugin,
              auth_attr,
              vnf_info,
              scale_vnf_request,
              region_name):
        pass

    def scale_update_wait(self,
                   context,
                   plugin,
                   auth_attr,
                   vnf_info,
                   region_name):
        lcm_op_occ = vnf_info.get('vnf_lcm_op_occ')
        vnf_instance_id = lcm_op_occ.get('vnf_instance_id')
        operation_params = jsonutils.loads(lcm_op_occ.get('operation_params'))
        scale_vnf_request = objects.ScaleVnfRequest.obj_from_primitive(
            operation_params, context=context)
        aspect_id = scale_vnf_request.aspect_id
        vnf_instance = objects.VnfInstance.get_by_id(context, vnf_instance_id)
        vnfd_dict = vnflcm_utils._get_vnfd_dict(context,
            vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)
        tosca = tosca_template.ToscaTemplate(
            parsed_params={}, a_file=False, yaml_dict_tpl=vnfd_dict,
            local_defs=toscautils.tosca_tmpl_local_defs())
        extract_policy_infos = vnflcm_utils.get_extract_policy_infos(tosca)

        policy = dict()
        policy['name'] = aspect_id
        policy['vnf_instance_id'] = lcm_op_occ.get('vnf_instance_id')
        policy['vdu_defs'] = vnflcm_utils.get_target_vdu_def_dict(
            extract_policy_infos=extract_policy_infos,
            aspect_id=scale_vnf_request.aspect_id,
            tosca=tosca)

        self.scale_wait(context, plugin, auth_attr, policy,
                        region_name, None)

    def get_cinder_list(self,
                        vnf_info):
        pass

    def get_grant_resource(self,
                   plugin,
                   vnf_instance,
                   vnf_info,
                   scale_vnf_request,
                   placement_obj_list,
                   vim_connection_info,
                   del_list):
        pass

    def get_rollback_ids(self,
                         plugin,
                         context,
                         vnf_dict,
                         aspect_id,
                         auth_attr,
                         region_name):
        return_id_list = []
        return_name_list = []
        return_grp_id = None
        return return_id_list, return_name_list, return_grp_id

    def sync_db(self, context, vnf_instance, vim_info):
        """method for database synchronization"""
        try:
            vdu_id_list = self._get_vdu_list(vnf_instance)

            for vdu_id in vdu_id_list:
                # get pod information
                for vnfc in (
                    vnf_instance.instantiated_vnf_info.vnfc_resource_info
                ):
                    if vnfc.vdu_id == vdu_id:
                        resource_type = (
                            vnfc.compute_resource.vim_level_resource_type)
                        resource_name = self._get_resource_name(
                            vnfc.compute_resource.resource_id, resource_type)
                        break
                pod_resources_from_k8s = self._get_pod_information(
                    resource_name, resource_type,
                    vnf_instance, vim_info
                )
                # check difference
                if not self._check_pod_information(vnf_instance, vdu_id,
                        pod_resources_from_k8s):
                    # no difference
                    continue

                # exec db sync
                try:
                    if self._database_update(context, vnf_instance,
                                             vdu_id):
                        LOG.info("Database synchronization succeeded. "
                                 f"vnf: {vnf_instance.id} vdu: {vdu_id}")

                except exceptions.VnfInstanceConflictState:
                    LOG.info("There is an LCM operation in progress, so "
                             "skip this DB synchronization. "
                             f"vnf: {vnf_instance.id}")

        except Exception as e:
            LOG.error(f"Failed to synchronize database vnf: "
                      f"{vnf_instance.id} Error: "
                      f"{encodeutils.exception_to_unicode(e)}")

    @check_vnf_state(action="db_sync",
        instantiation_state=[fields.VnfInstanceState.INSTANTIATED],
        task_state=[None])
    def _database_update(self, context, vnf_inst,
                         vdu_id):
        """Update tacker DB

        True: succeeded database update
        False: failed database update
        """
        # get target object
        vnf_instance = objects.VnfInstance.get_by_id(
            context, vnf_inst.id)
        if vnf_instance.instantiation_state != 'INSTANTIATED':
            return False

        # NOTE(fengyi): The operation_state in the opocc of vnf_instance
        # has FAILED_TEMP or FAILED, then Tacker cannot perform DB sync for
        # the vnf_instance.
        if k8s_utils.is_lcmocc_failure_status(context, vnf_inst.id):
            LOG.error(f"The LCM operation status of the vnf: {vnf_inst.id} "
                      f"is abnormal, so skip this DB synchronization.")
            return False

        # change task_state
        vnf_instance.task_state = fields.VnfInstanceTaskState.DB_SYNCHRONIZING
        vnf_instance.save()

        backup_vnf_instance = copy.deepcopy(vnf_instance)

        vim_info = vnflcm_utils.get_vim(
            context, vnf_instance.vim_connection_info)
        vim_connection_info = objects.VimConnectionInfo.obj_from_primitive(
            vim_info, context)

        # get pod information
        try:
            for vnfc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
                if vnfc.vdu_id == vdu_id:
                    resource_type = (
                        vnfc.compute_resource.vim_level_resource_type)
                    resource_name = self._get_resource_name(
                        vnfc.compute_resource.resource_id, resource_type)
                    break
            pod_resources_from_k8s = self._get_pod_information(
                resource_name, resource_type,
                vnf_instance, vim_connection_info
            )

            # check difference
            if not self._check_pod_information(vnf_instance, vdu_id,
                    pod_resources_from_k8s):
                vnf_instance.task_state = None
                vnf_instance.save()
                return False

            if self._sync_vnfc_resource_and_pod_resource(context,
                    vnf_instance, pod_resources_from_k8s, vdu_id):
                vnf_instance.task_state = None
                vnf_instance.save()
                return True

            vnf_instance = copy.deepcopy(backup_vnf_instance)
            vnf_instance.task_state = None
            vnf_instance.save()
            return False

        except Exception as e:
            LOG.error(f"Failed to update database vnf {vnf_instance.id} "
                    f"Error: {encodeutils.exception_to_unicode(e)}")
            vnf_instance = copy.deepcopy(backup_vnf_instance)
            vnf_instance.task_state = None
            vnf_instance.save()
            return False

    def _sync_vnfc_resource_and_pod_resource(self, context, vnf_instance,
         pod_resources_from_k8s, vdu_id):
        """Sync Pod name between k8s and tacker"""
        vnfc_count = 0
        for vnfc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
            if vnfc.vdu_id == vdu_id:
                vnfc_count += 1

        result = False
        # number of pod is same as k8s
        if vnfc_count == len(pod_resources_from_k8s):
            self._sync_resource_id(vnf_instance.instantiated_vnf_info,
                                   vdu_id, pod_resources_from_k8s)
            result = True
        # the number of pod is greater than k8s
        elif vnfc_count > len(pod_resources_from_k8s):
            result = self._delete_vnfc_resource(context, vnf_instance, vdu_id,
                pod_resources_from_k8s, vnfc_count)
        # the number of pod is less than k8s
        elif vnfc_count < len(pod_resources_from_k8s):
            result = self._add_vnfc_resource(context, vnf_instance, vdu_id,
                pod_resources_from_k8s, vnfc_count)

        return result

    def _delete_vnfc_resource(self, context, vnf_instance, vdu_id,
           pod_resources_from_k8s, vnfc_count):
        """Remove 'vnfcResourceInfo' with mismatched pod names"""
        delete_index = []
        for i, vnfc_resource_info in enumerate(
                vnf_instance.instantiated_vnf_info.vnfc_resource_info):
            if vnfc_resource_info.vdu_id != vdu_id:
                continue
            if vnfc_resource_info.compute_resource.resource_id not in (
                    set(pod_resources_from_k8s.keys())):
                delete_index.append(i)

        # For patterns where the number of pods is reduced and
        # the remaining pods are also renamed
        delete_cnt = vnfc_count - len(pod_resources_from_k8s)
        if delete_cnt != len(delete_index):
            for i in range(len(delete_index) - delete_cnt):
                del delete_index[-1]
        for idx in reversed(delete_index):
            del vnf_instance.instantiated_vnf_info.vnfc_resource_info[idx]

        self._sync_resource_id(vnf_instance.instantiated_vnf_info,
                               vdu_id, pod_resources_from_k8s)
        return self._calc_scale_level(context, vnf_instance, vdu_id,
                                len(pod_resources_from_k8s))

    def _add_vnfc_resource(self, context, vnf_instance, vdu_id,
            pod_resources_from_k8s, vnfc_count):
        """Add vnfcResourceInfo"""
        stored_pod_names = {
            vnfc.compute_resource.resource_id
            for vnfc in (
                vnf_instance.instantiated_vnf_info.vnfc_resource_info)
            if vnfc.vdu_id == vdu_id}
        add_pod_names = {
            pod_name for pod_name in (
                set(pod_resources_from_k8s.keys()))
            if pod_name not in stored_pod_names}

        # Determine the number of 'vnfc_resource_info' to add
        add_vnfc_resource_info_num = (
            len(pod_resources_from_k8s) - vnfc_count)
        for vnfc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
            if vnfc.vdu_id == vdu_id:
                resource_type = (
                    vnfc.compute_resource.vim_level_resource_type)
                metadata = vnfc.metadata[resource_type]
                break
        for dummy in range(add_vnfc_resource_info_num):
            resource_id = add_pod_names.pop()
            vnfc_resource = objects.VnfcResourceInfo()
            vnfc_resource.id = uuidutils.generate_uuid()
            vnfc_resource.vdu_id = vdu_id
            resource = objects.ResourceHandle()
            resource.resource_id = resource_id
            resource.vim_level_resource_type = resource_type
            vnfc_resource.compute_resource = resource
            vnfc_resource.metadata = {}
            vnfc_resource.metadata["Pod"] = (
                jsonutils.dumps(pod_resources_from_k8s.get(resource_id))
            )
            vnfc_resource.metadata[resource_type] = metadata
            vnf_instance.instantiated_vnf_info.vnfc_resource_info.append(
                vnfc_resource)

        self._sync_resource_id(vnf_instance.instantiated_vnf_info,
                               vdu_id, pod_resources_from_k8s)
        return self._calc_scale_level(context, vnf_instance, vdu_id,
                            len(pod_resources_from_k8s))

    def _check_pod_information(self, vnf_instance,
            vdu_id, pod_resources_from_k8s):
        """Compare 'instantiatedVnfInfo' and 'pod_resources_from_k8s' info

        True: find difference
        False: No difference
        """
        vnfc_rscs = vnf_instance.instantiated_vnf_info.vnfc_resource_info
        pod_names = {vnfc.compute_resource.resource_id for vnfc in vnfc_rscs
                    if vnfc.vdu_id == vdu_id}

        if len(pod_names) != len(pod_resources_from_k8s):
            return True

        # pod name check
        if pod_names != set(pod_resources_from_k8s.keys()):
            return True

        return False

    def _sync_resource_id(self, instantiated_vnf_info,
            vdu_id, pod_resources_from_k8s):
        """Set new resourceId into old resourceId"""
        match_pod_names = set()
        unmatch_pod_in_tacker = set()

        for vnfc in instantiated_vnf_info.vnfc_resource_info:
            if vnfc.vdu_id != vdu_id:
                continue

            if vnfc.compute_resource.resource_id in (
                    set(pod_resources_from_k8s.keys())):
                match_pod_names.add(
                    vnfc.compute_resource.resource_id)
            else:
                unmatch_pod_in_tacker.add(
                    vnfc.compute_resource.resource_id)

        # pickup new pod name
        new_pod_name = set(pod_resources_from_k8s.keys()) ^ match_pod_names

        for unmatch_pod_name in unmatch_pod_in_tacker:
            for vnfc in instantiated_vnf_info.vnfc_resource_info:
                if vnfc.vdu_id != vdu_id:
                    continue
                if vnfc.compute_resource.resource_id == (
                        unmatch_pod_name):
                    vnfc.compute_resource.resource_id = (
                        new_pod_name.pop()
                    )
                    vnfc.metadata["Pod"] = (
                        jsonutils.dumps(
                            pod_resources_from_k8s.get(
                                (vnfc.compute_resource.resource_id)
                            )
                        )
                    )
                    break

    def _calc_scale_level(self, context, vnf_instance,
            vdu_id, current_pod_num):
        """calc scale_level and set"""
        vnfd = vnflcm_utils.get_vnfd_dict(context,
            vnf_instance.vnfd_id,
            vnf_instance.instantiated_vnf_info.flavour_id)

        policies = vnfd.get("topology_template", {}).get("policies", {})
        for policy in policies:
            for v in policy.values():
                if (v.get("type") == (
                        "tosca.policies.nfv.VduScalingAspectDeltas")):
                    if vdu_id in v.get("targets", []):
                        aspect_id = v.get("properties", {}).get("aspect")
                        break
        step_deltas = (self._get_scale_value(policies, aspect_id))

        for policy in policies:
            for v in policy.values():
                if (v.get("type") == (
                    "tosca.policies.nfv.VduScalingAspectDeltas")
                        and step_deltas
                        and vdu_id in v.get("targets", [])):
                    delta = (v.get("properties", {})
                             .get("deltas", {})
                             .get(step_deltas, {})
                             .get("number_of_instances"))
                elif (v.get("type") == (
                        "tosca.policies.nfv.VduInitialDelta")
                      and vdu_id in v.get("targets", [])):
                    initial_delta = (v.get("properties", {})
                                      .get("initial_delta", {})
                                      .get("number_of_instances"))
        if (current_pod_num - initial_delta) % delta != 0:
            LOG.error("Error computing 'scale_level'. "
                      f"current Pod num: {current_pod_num} delta: {delta}. "
                      f"vnf: {vnf_instance.id} vdu: {vdu_id}")
            return False

        scale_level = (current_pod_num - initial_delta) // delta

        for inst_vnf in vnf_instance.instantiated_vnf_info.scale_status:
            if inst_vnf.aspect_id == aspect_id:
                inst_vnf.scale_level = scale_level
                break

        return self._check_pod_range(vnf_instance, vnfd, vdu_id,
                current_pod_num)

    def _get_scale_value(self, policies, aspect_id):
        """get step_deltas from vnfd"""
        for policy in policies:
            for v in policy.values():
                if v.get("type") == "tosca.policies.nfv.ScalingAspects":
                    step_deltas = (v.get("properties", {})
                                   .get("aspects", {})
                                   .get(aspect_id, {})
                                   .get("step_deltas", [])[0])
                    break
        return step_deltas

    def _check_pod_range(self, vnf_instance, vnfd, vdu_id,
            current_pod_num):
        """Check the range of the maximum or minimum number of pods.

        If it finds out of range, output a error log and do not update
        database.
        """
        vdu_profile = (vnfd.get("topology_template", {})
                           .get("node_templates", [])
                           .get(vdu_id, {})
                           .get("properties", {})
                           .get("vdu_profile"))
        max_number_of_instances = vdu_profile.get("max_number_of_instances")
        min_number_of_instances = vdu_profile.get("min_number_of_instances")

        if (current_pod_num > max_number_of_instances
                or current_pod_num < min_number_of_instances):
            LOG.error(f"Failed to update database vnf {vnf_instance.id} "
                      f"vdu: {vdu_id}. Pod num is out of range. "
                      f"pod_num: {current_pod_num}")
            return False
        return True

    def _get_pod_information(self, resource_name,
            resource_type, vnf_instance, vim_connection_info):
        """Extract a Pod starting with the specified 'resource_name' name"""
        namespace = vnf_instance.vnf_metadata.get('namespace')
        if not namespace:
            namespace = "default"
        auth_attr = vim_connection_info.access_info
        auth_cred, _ = self.get_auth_creds(auth_attr)

        core_v1_api_client = self.kubernetes.get_core_v1_api_client(
            auth=auth_cred)
        resource_pods = {}
        all_pods = core_v1_api_client.list_namespaced_pod(
            namespace=namespace)

        for pod in all_pods.items:
            if self.is_match_pod_naming_rule(resource_type,
                  resource_name, pod.metadata.name):
                resource_pods[pod.metadata.name] = pod.metadata.to_dict()

        return resource_pods

    def _get_vdu_list(self, vnf_instance):
        """get vdu_list"""
        vdu_id_list = set()

        for vnfc in vnf_instance.instantiated_vnf_info.vnfc_resource_info:
            if vnfc.compute_resource.resource_id != "":
                vdu_id_list.add(vnfc.vdu_id)
        return vdu_id_list

    def _get_resource_name(self, resource_id, resource_type):
        """get resource name"""
        if resource_type == 'Pod':
            resource_name = resource_id
        else:
            name_list = resource_id.split("-")
            if resource_type == 'Deployment':
                del name_list[-2:]
            elif resource_type in ('ReplicaSet', 'DaemonSet', 'StatefulSet'):
                del name_list[-1]
            resource_name = '-'.join(name_list)

        return resource_name
