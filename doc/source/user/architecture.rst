===================
Tacker Architecture
===================

The following diagram shows the overview of the Tacker architecture

.. figure:: /_images/tacker-design.svg


Packages:

* **tacker** - is the main package for Tacker project.

Components:

* **server** - provides *REST API* and calls conductor via RPC.
* **tacker-conductor** - implements all logics to operate VNF and call required
  drivers providing interface to NFV infrastructures.

* **VnfPm/VnfFmController** - is responsible for exact actions
  to configure of PM/FM.
* **VnfLcmController** - is responsible for exact actions to
  configure of LCM.
* **PrometheusPlugin** - is responsible for exact actions to
  configure Prometheus.

* **VnfPm/VnfFmDriver** - is responsible for send notification to NFVO.
* **VnfLcmDriver** - is responsible for exact action to
  mgmt driver or infra driver.

* **MgmtDriver** - is responsible for exact actions to configure VNFs.
* **InfraDriver** - is responsible for exact actions to operate OpenStack or
  Kubernates.

APIs:

Tacker consists of three independent versions: Legacy, v1, and v2.
Each version is separated by API and has the following functions.

.. note::

  Tacker was originally designed to have both NFVO and VNFM functionalities
  that are now called Legacy API and the most parts have already been
  deprecated except for VIM Management which is left mainly for debugging
  purposes.
  ETSI NFV-SOL API, on the other hand, is a brand new design that provides
  Generic VNFM functionality in compliance with the ETSI NFV standard.


.. list-table:: API versions
  :widths: 2 1 3 5
  :header-rows: 1

  * - API type
    - Version
    - Function
    - ETSI NFV-SOL Version
  * - Legacy API
    - Legacy
    - `VIM Management`_
    - None
  * - ESTI NFV-SOL API
    - v1
    - `v1 VNF Lyfecycle Management`_
    - | `ETSI NFV-SOL002 2.6.1`_
      | `ETSI NFV-SOL003 2.6.1`_
      | `ETSI NFV-SOL013 3.4.1`_
  * - ESTI NFV-SOL API
    - v1
    - `VNF Package Management`_
    - | `ETSI NFV-SOL004 2.6.1`_
      | `ETSI NFV-SOL005 2.6.1`_
  * - ESTI NFV-SOL API
    - v2
    - `v2 VNF Lyfecycle Management`_
    - | `ETSI NFV-SOL002 3.3.1`_ (\*1)
      | `ETSI NFV-SOL003 3.3.1`_
      | `ETSI NFV-SOL013 3.4.1`_ (\*2)
  * - ESTI NFV-SOL API
    - v2
    - `VNF Performance Management`_
    - | `ETSI NFV-SOL002 3.3.1`_
      | `ETSI NFV-SOL003 3.3.1`_
      | `ETSI NFV-SOL013 3.4.1`_ (\*2)
  * - ESTI NFV-SOL API
    - v2
    - `VNF Fault Management`_
    - | `ETSI NFV-SOL002 3.3.1`_
      | `ETSI NFV-SOL003 3.3.1`_
      | `ETSI NFV-SOL013 3.4.1`_ (\*2)


(\*1)The functionality related to VNF LCM Coordination in
Change current VNF package complies with `ETSI NFV-SOL002 3.6.1`_.

(\*2)OAUTH2_CLIENT_CERT in SubscriptionAuthentication is compliant with
`ETSI NFV-SOL013 3.5.1`_.


.. note::

  See `Tacker Horizon User Guide`_ details on APIs
  supported by Tacker Horizon.


Supported versions:

[2024.1 Caracal / 2024.2 Dalmatian]

* **Kubernetes 1.26** - is supported from 2023.2 Bobcat to 2024.2 Dalmatian.
* **Helm 3.11** - is supported from 2023.2 Bobcat to 2024.2 Dalmatian.
* **Prometheus 2.45** - is supported from 2023.2 Bobcat onwards.
* **Alertmanager 0.26** - is supported from 2023.2 Bobcat onwards.

[2025.1 Epoxy]

* **Kubernetes 1.30** - is supported from 2025.1 Epoxy onwards.
* **Helm 3.15** - is supported from 2025.1 Epoxy onwards.
* **Prometheus 2.45** - is supported from 2023.2 Bobcat onwards.
* **Alertmanager 0.26** - is supported from 2023.2 Bobcat onwards.


Tacker Service
--------------

Tacker service is composed of two main processes:

* tacker.service
* tacker-conductor.service

*tacker.service* is a web server with Web Server Gateway Interface (WSGI)
waiting for the REST API calls and it passes some operations to the
*tacker-conductor.service* via RPC. Two types of API are supported;
ETSI NFV-SOL API and Legacy API.

*tacker-conductor.service* implements some complicated logic and operations
for orchestrations and VNF managements. It is mainly responsible for ETSI
NFV-SOL based API operations and communicates with OpenStack or Kubernetes
VIM by the infra drivers.


ETSI NFV-SOL Tacker Implementation
----------------------------------

Tacker ETSI NFV-SOL based implementation is described as the following:

.. figure:: /_images/tacker-design-etsi.svg


When a REST API call is sent to tacker-server, some simple operations are
executed in tacker-server with DB queries. The others are delegated to
`Conductor Server` via RPC, and `VNF Lifecycle Driver` calls appropriate
infra-driver to execute the actual logics for control and management of
virtualised resources.

Below is an example of resources created/configured when Openstack InfraDriver
is used.

.. figure:: /_images/openstack_infra_driver.svg


OpenStack InfraDriver uses Nova Instance, Cinder Storage, Neutron Port, etc.
as resources to configure VNFC.

And below is an example of resources created/configured when Kubernetes/Helm
InfraDriver is used.

.. figure:: /_images/k8s_helm_infra_driver.svg


Kubernetes/Helm InfraDriver uses Pods, Containers, etc. as resources
to configure VNFC.
In addition to these, Volume, ConfigMap, Secret, etc. are also used as
resources to configure VNF Instance.

Tacker also provides a framework to enable lifecycle hooks called mgmt-driver.
See `v1 Management Driver`_ and `v2 Management Driver`_ for details.

.. note::

  VIM Management operations such as "Register VIM" and "Update VIM" are
  not defined in ETSI NFV-SOL.
  Users may need to use Legacy Tacker or an external NFVO.


Legacy Tacker Implementation
----------------------------

Legacy Tacker implementation is described as the following:

.. figure:: /_images/tacker-design-legacy.svg


When a REST API call is sent to tacker-server, VNFM and NFVO plugins handle
the request and execute connected methods in each plugin. The NFVO plugin
invokes required vim-driver methods.

.. warning::

  Legacy API features other than the VIM feature have been deprecated.
  So only Nfvo receives the API from the tacker-client, but Vnfm and
  VNFMPlugin remain because they are used by v1 VNF Lyfecycle Management.


.. _ETSI NFV-SOL002 2.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/02.06.01_60/gs_nfv-sol002v020601p.pdf
.. _ETSI NFV-SOL002 3.3.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.03.01_60/gs_nfv-sol002v030301p.pdf
.. _ETSI NFV-SOL002 3.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/002/03.06.01_60/gs_nfv-sol002v030601p.pdf
.. _ETSI NFV-SOL003 2.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/02.06.01_60/gs_nfv-sol003v020601p.pdf
.. _ETSI NFV-SOL003 3.3.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/003/03.03.01_60/gs_nfv-sol003v030301p.pdf
.. _ETSI NFV-SOL004 2.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/004/02.06.01_60/gs_nfv-sol004v020601p.pdf
.. _ETSI NFV-SOL005 2.6.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/005/02.06.01_60/gs_nfv-sol005v020601p.pdf
.. _ETSI NFV-SOL013 3.4.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.04.01_60/gs_nfv-sol013v030401p.pdf
.. _ETSI NFV-SOL013 3.5.1:
  https://www.etsi.org/deliver/etsi_gs/NFV-SOL/001_099/013/03.05.01_60/gs_nfv-sol013v030501p.pdf
.. _VIM Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v1/legacy.html
.. _VNF Package Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v1/vnfpkgm.html
.. _v1 VNF Lyfecycle Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v1/vnflcm.html
.. _v2 VNF Lyfecycle Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnflcm.html
.. _VNF Performance Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnfpm.html
.. _VNF Fault Management:
  https://docs.openstack.org/api-ref/nfv-orchestration/v2/vnffm.html
.. _v1 Management Driver:
  https://docs.openstack.org/tacker/latest/user/etsi_use_case_guide.html#management-driver
.. _v2 Management Driver:
  https://docs.openstack.org/tacker/latest/user/v2/use_case_guide.html#management-driver
.. _Tacker Horizon User Guide: https://docs.openstack.org/tacker-horizon/latest/user/index.html
