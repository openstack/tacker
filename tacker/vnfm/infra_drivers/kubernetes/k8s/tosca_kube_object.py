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


class ToscaKubeObject(object):

    """ToscaKubeObject holds the basic struct of a VDU.

    That is used for translating TOSCA to Kubernetes templates.
    """

    def __init__(self, name=None, namespace=None, mapping_ports=None,
                 containers=None, network_name=None,
                 mgmt_connection_point=False, scaling_object=None,
                 service_type=None, labels=None, annotations=None):
        self._name = name
        self._namespace = namespace
        self._mapping_ports = mapping_ports
        self._containers = containers
        self._network_name = network_name
        self._mgmt_connection_point = mgmt_connection_point
        self._scaling_object = scaling_object
        self._service_type = service_type
        self._labels = labels
        self._annotations = annotations

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def namespace(self):
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        self._namespace = namespace

    @property
    def mapping_ports(self):
        return self._mapping_ports

    @mapping_ports.setter
    def mapping_ports(self, mapping_ports):
        self._mapping_ports = mapping_ports

    @property
    def containers(self):
        return self._containers

    @containers.setter
    def containers(self, containers):
        self._containers = containers

    @property
    def network_name(self):
        return self._network_name

    @network_name.setter
    def network_name(self, network_name):
        self._network_name = network_name

    @property
    def mgmt_connection_point(self):
        return self._mgmt_connection_point

    @mgmt_connection_point.setter
    def mgmt_connection_point(self, mgmt_connection_point):
        self._mgmt_connection_point = mgmt_connection_point

    @property
    def scaling_object(self):
        return self._scaling_object

    @scaling_object.setter
    def scaling_object(self, scaling_object):
        self._scaling_object = scaling_object

    @property
    def service_type(self):
        return self._service_type

    @service_type.setter
    def service_type(self, service_type):
        self._service_type = service_type

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        self._labels = labels

    @property
    def annotations(self):
        return self._annotations

    @annotations.setter
    def annotations(self, annotations):
        self._annotations = annotations


class Container(object):
    """Container holds the basic structs of a container"""
    def __init__(self, name=None, num_cpus=None, mem_size=None, image=None,
                 command=None, args=None, ports=None, config=None):
        self._name = name
        self._num_cpus = num_cpus
        self._mem_size = mem_size
        self._image = image
        self._command = command
        self._args = args
        self._ports = ports
        self._config = config

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def num_cpus(self):
        return self._num_cpus

    @num_cpus.setter
    def num_cpus(self, num_cpus):
        self._num_cpus = num_cpus

    @property
    def mem_size(self):
        return self._mem_size

    @mem_size.setter
    def mem_size(self, mem_size):
        self._mem_size = mem_size

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image):
        self._image = image

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, command):
        self._command = command

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, args):
        self._args = args

    @property
    def ports(self):
        return self._ports

    @ports.setter
    def ports(self, ports):
        self._ports = ports

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config


class ScalingObject(object):
    """ScalingObject holds the basic struct of a horizontal pod auto-scaling"""
    def __init__(self, scaling_name=None, min_replicas=None, max_replicas=None,
                 scale_target_name=None,
                 target_cpu_utilization_percentage=None):
        self._scaling_name = scaling_name
        self._min_replicas = min_replicas
        self._max_replicas = max_replicas
        self._scale_target_name = scale_target_name
        self._target_cpu_utilization_percentage = \
            target_cpu_utilization_percentage

    @property
    def scaling_name(self):
        return self._scaling_name

    @scaling_name.setter
    def scaling_name(self, scaling_name):
        self._scaling_name = scaling_name

    @property
    def min_replicas(self):
        return self._min_replicas

    @min_replicas.setter
    def min_replicas(self, min_replicas):
        self._min_replicas = min_replicas

    @property
    def max_replicas(self):
        return self._max_replicas

    @max_replicas.setter
    def max_replicas(self, max_replicas):
        self._max_replicas = max_replicas

    @property
    def scale_target_name(self):
        return self._scale_target_name

    @scale_target_name.setter
    def scale_target_name(self, scale_target_name):
        self._scale_target_name = scale_target_name

    @property
    def target_cpu_utilization_percentage(self):
        return self._target_cpu_utilization_percentage

    @target_cpu_utilization_percentage.setter
    def target_cpu_utilization_percentage(self,
                                          target_cpu_utilization_percentage):
        self._target_cpu_utilization_percentage = \
            target_cpu_utilization_percentage
