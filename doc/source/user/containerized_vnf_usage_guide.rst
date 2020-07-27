====================================================
Experimenting containerized VNFs with Kubernetes VIM
====================================================

In the past, Tacker only supports creating virtual machine based VNF using
Heat. This section covers how to deploy `containerized VNF` using Kubernetes
VIM in Tacker.

Prepare Kubernetes VIM
======================

To use Kubernetes type of VNF, firstly user must register Kubernetes VIM.
Tacker supports Kubernetes authentication with two types: basic authentication
(username and password) or Bearer token. User can secure the connection to
Kubernetes cluster by providing SSL certificate. The following
``vim-config.yaml`` file provides necessary information to register a
Kubernetes VIM.

.. code-block:: console

  auth_url: "https://192.168.11.110:6443"
  username: "admin"
  password: "admin"
  project_name: "default"
  ssl_ca_cert: None
  type: "kubernetes"

More details about registering Kubernetes VIM, please refer [#first]_

Sample container TOSCA templates
================================

1. One container per VDU example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, because Kubernetes does not support multiple networks such as
choosing networks, connection points for applications, therefore users only
deploys their applications with default networks (Pod and Service networks).
In this case, user need to provide only information about VDU to create a VNF
in Tacker.

The following example shows TOSCA template of containerized VNF for pure
Kubernetes environment with one container per VDU.

**tosca-vnfd-containerized-two-containers.yaml**

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
  description: A sample containerized VNF with two containers per VDU

  metadata:
      template_name: sample-tosca-vnfd

  topology_template:
    node_templates:
      VDU1:
        type: tosca.nodes.nfv.VDU.Tacker
        properties:
          namespace: default
          mapping_ports:
            - "80:80"
            - "88:88"
          service_type: NodePort
          vnfcs:
            front_end:
              num_cpus: 0.5
              mem_size: 512 MB
              image: nginx
              ports:
                - "80"
            rss_reader:
              num_cpus: 0.5
              mem_size: 512 MB
              image: nickchase/rss-php-nginx:v1
              ports:
                - "88"
    policies:
      - SP1:
          type: tosca.policies.tacker.Scaling
          targets: [VDU1]
          properties:
            min_instances: 1
            max_instances: 3
            target_cpu_utilization_percentage: 40

In "vnfcs", there are 2 components: front_end and rss_reader.
We model them as Containers [#second]_ inside a Pod [#third]_. To provide
recover ability of these containers, we put all of containers inside a
Deployment [#fourth]_ object, that can warrant the number of replica with
auto-healing automatically.

The following table shows details about parameter of a Container. Config is
translated to ConfigMap [#fifth]_, when user want to update the VNF (config),
equivalent ConfigMap will be updated.

.. code-block:: console

  +-----------------------------------------------------------------------------------------------+
  |          vnfcs          |            Example            |               Description           |
  +-----------------------------------------------------------------------------------------------+
  |          name           |           front_end           |  Name of container                  |
  +-----------------------------------------------------------------------------------------------+
  |        num_cpus         |              0.5              |  Number of CPUs                     |
  +-----------------------------------------------------------------------------------------------+
  |        mem_size         |            512 MB             |  Memory size                        |
  +-----------------------------------------------------------------------------------------------+
  |         image           |             nginx             |  Image to launch container          |
  +-----------------------------------------------------------------------------------------------+
  |         ports           |            - "80"             |  Exposed ports in container         |
  +-----------------------------------------------------------------------------------------------+
  |        command          |      ['/bin/sh','echo']       |  Command when container was started |
  +-----------------------------------------------------------------------------------------------+
  |         args            |          ['hello']            |  Args of command                    |
  +-----------------------------------------------------------------------------------------------+
  |        config           |         param0: key1          |  Set variables                      |
  |                         |         param1: key2          |                                     |
  +-----------------------------------------------------------------------------------------------+

In Tacker, VDU is modeled as a Service [#sixth]_ in Kubernetes. Because Pods
can be easily replaced by others, when the number of replica increased,
workload should be shared between Pods. To do this task, we model VDU as
Service, it acts as a Load balancer for Pods. Currently, we support some
parameters as the following table.

.. code-block:: console

  +--------------------------------------------------------------------------------------------------------------------------------+
  |     VDU properties      |          Example          |            Description                                                   |
  +--------------------------------------------------------------------------------------------------------------------------------+
  |       namespace         |          default          | Namespace in Kubernetes where all objects are deployed                   |
  +--------------------------------------------------------------------------------------------------------------------------------+
  |     mapping_ports       |         - "443:443"       | Published ports and target ports (container ports) of Service Kubernetes |
  |                         |         - "80:8080"       |                                                                          |
  +--------------------------------------------------------------------------------------------------------------------------------+
  |       labels            |      "app: webserver"     | Labels which is set for Kubernetes objects, it is used as Selector to    |
  |                         |                           | Service can send requests to Pods                                        |
  +--------------------------------------------------------------------------------------------------------------------------------+
  |     service_type        |         ClusterIP         | Set service type for Service object.                                     |
  |                         |                           |                                                                          |
  +--------------------------------------------------------------------------------------------------------------------------------+
  |         vnfcs           |                           | Vnfcs are modeled by Containers and Deployment object. User can limit    |
  |                         |                           | resource, set image, publish container ports, set commands and variables |
  +--------------------------------------------------------------------------------------------------------------------------------+

User can also set scaling policy for VDU by adding the following policy. These
information is translated to Horizontal Pod Autoscaler in Kubernetes. In the
current scope, we just support auto-scaling with CPU utilization, more metrics
will be added in the future.

.. code-block:: yaml

  policies:
    - SP1:
        type: tosca.policies.tacker.Scaling
        targets: [VDU1]
        properties:
          min_instances: 1
          max_instances: 3
          target_cpu_utilization_percentage: 40

2. Two containers per VDU example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to the above example, in this scenario, we define 2 containers in VDU1.

**tosca-vnfd-containerized.yaml**

.. code-block:: yaml

  tosca_definitions_version: tosca_simple_profile_for_nfv_1_0_0
  description: A sample containerized VNF with two containers per VDU

  metadata:
      template_name: sample-tosca-vnfd

  topology_template:
    node_templates:
      VDU1:
        type: tosca.nodes.nfv.VDU.Tacker
        properties:
          namespace: default
          mapping_ports:
            - "80:8080"
          labels:
            - "app: webserver"
          service_type: ClusterIP
          vnfcs:
            web_server:
                num_cpus: 0.5
                mem_size: 512 MB
                image: celebdor/kuryr-demo
                ports:
                  - "8080"
                config: |
                  param0: key1
                  param1: key2

    policies:
      - SP1:
          type: tosca.policies.tacker.Scaling
          targets: [VDU1]
          properties:
            min_instances: 1
            max_instances: 3
            target_cpu_utilization_percentage: 40

Viewing a containerized VNF
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create sample containerized VNF

.. code-block:: console

  $ openstack vnf descriptor create --vnfd-file tosca-vnfd-containerized.yaml VNFD1
  Created a new vnfd:
  +-----------------+-------------------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                                 |
  +-----------------+-------------------------------------------------------------------------------------------------------+
  | created_at      | 2018-01-21 14:36:51.757044                                                                            |
  | description     | A sample containerized VNF with one container per VDU                                                 |
  | id              | fb4a0aa8-e410-4e73-abdc-d2808de155ef                                                                  |
  | name            | VNFD1                                                                                                 |
  | service_types   | vnfd                                                                                                  |
  | template_source | onboarded                                                                                             |
  | tenant_id       | 2d22508be9694091bb2f03ce27911416                                                                      |
  | updated_at      |                                                                                                       |
  +-----------------+-------------------------------------------------------------------------------------------------------+

  $ openstack vnf create --vnfd-name VNFD1 --vim-name vim-kubernetes VNF1
  Created a new vnf:
  +----------------+-------------------------------------------------------------------------------------------------------+
  | Field          | Value                                                                                                 |
  +----------------+-------------------------------------------------------------------------------------------------------+
  | created_at     | 2018-01-21 14:37:23.318018                                                                            |
  | description    | A sample containerized VNF with one container per VDU                                                 |
  | error_reason   |                                                                                                       |
  | id             | 1faf776b-8d2b-4ee6-889d-e3b7c7310411                                                                  |
  | instance_id    | default,svc-vdu1-05db44                                                                               |
  | mgmt_ip_address|                                                                                                       |
  | name           | VNF1                                                                                                  |
  | placement_attr | {"vim_name": "vim-kubernetes"}                                                                        |
  | status         | PENDING_CREATE                                                                                        |
  | tenant_id      | 2d22508be9694091bb2f03ce27911416                                                                      |
  | updated_at     |                                                                                                       |
  | vim_id         | 791830a6-45fd-468a-bd85-e07fe24e5ce3                                                                  |
  | vnfd_id        | fb4a0aa8-e410-4e73-abdc-d2808de155ef                                                                  |
  +----------------+-------------------------------------------------------------------------------------------------------+

  $ openstack vnf list
  +--------------------------------------+------+----------------------------+--------+--------------------------------------+--------------------------------------+
  | id                                   | name | mgmt_ip_address            | status | vim_id                               | vnfd_id                              |
  +--------------------------------------+------+----------------------------+--------+--------------------------------------+--------------------------------------+
  | 1faf776b-8d2b-4ee6-889d-e3b7c7310411 | VNF1 |                            | ACTIVE | 791830a6-45fd-468a-bd85-e07fe24e5ce3 | fb4a0aa8-e410-4e73-abdc-d2808de155ef |
  +--------------------------------------+------+----------------------------+--------+--------------------------------------+--------------------------------------+

To test VNF is running in Kubernetes environment, we can check by running
following commands

.. code-block:: console

  $ kubectl get svc
  NAME              TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)   AGE
  kubernetes        ClusterIP   192.168.28.129   <none>        443/TCP   5h
  svc-vdu1-05db44   ClusterIP   192.168.28.187   <none>        80/TCP    12m

  $ kubectl get deployment
  NAME              DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
  svc-vdu1-05db44   1         1         1            1           16m

  $ kubectl get pod
  NAME                               READY     STATUS    RESTARTS   AGE
  svc-vdu1-05db44-7dcb6b955d-wkh7d   1/1       Running   0          18m

  $ kubectl get hpa
  NAME              REFERENCE                    TARGETS           MINPODS   MAXPODS   REPLICAS   AGE
  svc-vdu1-05db44   Deployment/svc-vdu1-05db44   <unknown> / 40%   1         3         1          17m

  $ kubectl get configmap
  NAME              DATA      AGE
  svc-vdu1-05db44   2         17m

User also can scale VNF manually, by running the following commands:

.. code-block:: console

  $ openstack vnf scale --vnf-name VNF1 --scaling-policy-name SP1 --scaling-type out

  $ kubectl get deployment
  NAME              DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
  svc-vdu1-651815   2         2         2            1           3h

  $ kubectl get pods
  NAME                               READY     STATUS    RESTARTS   AGE
  svc-vdu1-651815-5b894b8bfb-b6mzq   2/2       Running   0          3h
  svc-vdu1-651815-5b894b8bfb-b7f2c   2/2       Running   0          40s

In the same way, user also scale in VNF with scaling-type is 'in'. The range
of scaling manually is limited by 'min_instances' and 'max_instances' user
provide in VNF template.

Multi-Interface for C-VNF
=========================

To use multi-interface for C-VNF, User should follow below procedure.

1. Checking kuryr.conf
~~~~~~~~~~~~~~~~~~~~~~

After installation, user should check kuryr.conf configuration.

.. code-block:: console

  $ sudo cat /etc/kuryr/kuryr.conf | grep multi_vif_drivers
  multi_vif_drivers = npwg_multiple_interfaces

2. Adding K8s CustomResourceDefinition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use CustomResourceDefinition, user needs to add CRD.
User can make a additional network using yaml file like below.
Create yaml file like below and register it.

.. code-block:: console

  $ cat ./crdnetwork.yaml

.. code-block:: yaml

  apiVersion: apiextensions.k8s.io/v1beta1
  kind: CustomResourceDefinition
  metadata:
    name: network-attachment-definitions.k8s.cni.cncf.io
  spec:
    group: k8s.cni.cncf.io
    version: v1
    scope: Namespaced
    names:
      plural: network-attachment-definitions
      singular: network-attachment-definition
      kind: NetworkAttachmentDefinition
      shortNames:
      - net-attach-def
    validation:
      openAPIV3Schema:
        properties:
          spec:
            properties:
              config:
                   type: string

Register crdnetwork.yaml

.. code-block:: console

  $ kubectl create -f ~/crdnetwork.yaml

Get crd list

.. code-block:: console

  $ kubectl get crd

  NAME                                             CREATED AT
  kuryrnetpolicies.openstack.org                   2019-07-31T02:23:54Z
  kuryrnets.openstack.org                          2019-07-31T02:23:54Z
  network-attachment-definitions.k8s.cni.cncf.io   2019-07-31T02:23:55Z

3. Adding neutron subnet id information to k8s CRD
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To use neutron subnet in kubernetes, user should register neutron
subnet to CRD. At first, user should create subnet.yaml file.

.. code-block:: console

  $ cat ./kuryr-subnetname1.yaml

  apiVersion: "k8s.cni.cncf.io/v1"
  kind: NetworkAttachmentDefinition
  metadata:
    name: subnetname1
    annotations:
      openstack.org/kuryr-config: '{"subnetId": "$subnet_id"}'

After making a yaml file, user should create subnet with yaml file.

.. code-block:: console

  $ kubectl create -f ~/kuryr-subnetname1.yaml


After created, user can check subnet info like below.

.. code-block:: console

  $ kubectl get net-attach-def

  NAME           AGE
  k8s-multi-10   7d
  k8s-multi-11   7d


Known Issues and Limitations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Does not support Volumes in Kubernetes
- Horizontal Pod AutoScaler only support CPU utilization
- Add support Kuryr-Kubernetes for making hybrid network in the future

References
==========
.. [#first] https://opendev.org/openstack/tacker/src/branch/master/doc/source/install/kubernetes_vim_installation.rst
.. [#second] https://kubernetes.io/docs/concepts/workloads/pods/init-containers
.. [#third] https://kubernetes.io/docs/concepts/workloads/pods/pod-overview
.. [#fourth] https://kubernetes.io/docs/concepts/workloads/controllers/deployment
.. [#fifth] https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap
.. [#sixth] https://kubernetes.io/docs/concepts/services-networking/service
