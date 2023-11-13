==================================
Enhanced Tacker Policy Usage Guide
==================================

Overview
--------

The default Tacker API policy only supports whether the user can access the
API, but does not determine whether the users can access the resource on which
the API call operates.

Enhanced Tacker Policy enables Users to get finer-grained access control based
on user and VNF information for API resources.

This document describes how to use Enhanced Tacker Policy in Tacker.


Introduction to enhanced tacker attributes
------------------------------------------

Enhanced Tacker Policy function currently supports three enhanced attributes:
area, vendor, and tenant.

* area: Area attribute is an area-region pair. The value of this attribute is a
  string in the format of "area@region". This attribute describes the area
  where VIM or VNF is located.
* vendor: Vendor attribute is the name of the vendor. It is defined in the
  definition file of VNF package. VNF obtains this attribute from VNF package.
* tenant: Tenant attribute is the name of the tenant. This attribute describes
  the namespace of CNF, and the project name of VNF.


Enable Enhanced Tacker Policy
-----------------------------

Enhanced Tacker Policy is disabled by default in Tacker.
For it to work, user needs to find ``enhanced_tacker_policy`` in
``tacker.conf`` and change its value to ``True``. If not found, please add it
yourself.

.. code-block:: console

  $ vi /etc/tacker/tacker.conf
  ...
  [oslo_policy]
  enhanced_tacker_policy = True
  ...


Configure Enhanced Policy Rules
-------------------------------

The `oslo.policy`_ supports the function to compare API attributes
to object attributes.
Based on this function, Enhanced Tacker Policy function currently supports
three enhanced tacker attributes: area, vendor, and tenant.

.. code-block:: yaml

  "get_vim" : "area:%(area)s"
  "os_nfv_orchestration_api:vnf_packages:show" : "vendor:%(vendor)s"
  "os_nfv_orchestration_api:vnf_instances:show" : "tenant:%(tenant)s"


Take the area attribute as an example, the area string before the colon is an
API attribute, namely the area of the API user. It is compared with the area of
the object (in this case, a VNF instance). More precisely, it is compared with
the area field of that object in the database. If the two values are equal,
permission is granted.

For the policy rule configuration used in this usage guide, please refer to the
`Sample policy.yaml file`_ chapter in the Appendix.


Create user with special roles
------------------------------

Users need to define special roles with the following naming rules to represent
users with access rights to corresponding resources. For example, a user with a
role of ``VENDOR_company-a`` has permission to access resources whose vendor
attribute is ``company-a``. This is because in implementation, Tacker will
convert special roles into user attributes according to the following
conversion rules for attribute comparison.


Special Roles' Naming Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enhanced Tacker Policy defines the following naming rules for special roles.
Admin user need to create special roles according to these naming rules,
otherwise Tacker will not correctly convert these special roles into user
attributes.

#.  The role name consists of three parts: prefix + "_" + [attribute
    value/special value]
#.  Supported prefixes, attribute values and special values are shown in the
    following table:

    .. list-table::
      :widths: 10 14 12 50
      :header-rows: 1

      * - Prefix
        - Attribute value
        - Special value
        - Sample
      * - AREA
        - area value
        - all@all, all@{region_value}
        - AREA_tokyo@japan, AREA_all@all, AREA_all@japan
      * - VENDOR
        - vendor value
        - all
        - VENDOR_company_a, VENDOR_all
      * - TENANT
        - tenant value
        - all
        - TENANT_default, TENANT_all

    .. note::

      As "all" is treated as a special value, the above attribute of resource
      cannot use "all" as the attribute value.


Conversion rules
~~~~~~~~~~~~~~~~

In Tacker implementation, Tacker converts these special roles into API
attributes and provide them to Tacker policy. The conversion follows the
following rules:

#.  For ordinary attribute values, they will be directly converted to user
    attribute values.

    .. list-table::
      :widths: 10 14 50
      :header-rows: 1

      * - Prefix
        - Attribute Name
        - Sample (special role -> user attribute value)
      * - AREA
        - area
        - AREA_tokyo@japan -> {"area": ["tokyo@japan"]}
      * - VENDOR
        - vendor
        - VENDOR_company-a -> {"vendor": ["company-a"]}
      * - TENANT
        - tenant
        - TENANT_default -> {"tenant": ["default"]}


#.  For special value in Enhanced Tacker Policy, the corresponding attribute
    value of resource will be assigned to user.

    .. list-table::
      :widths: 10 14 14 50
      :header-rows: 1

      * - Prefix
        - Attribute Name
        - Special Value
        - Sample (resource attribute -> user attribute)
      * - AREA
        - area
        - all@all
        - {"area": "tokyo@japan"} -> {"area": ["tokyo@japan"]}
      * - AREA
        - area
        - all@{region_value}
        - same region value:

          .. code-block:: console

            {"area": "tokyo@japan"} -> {"area": ["tokyo@japan"]}


          different region value:

          .. code-block:: console

            any -> {"area": []}


      * - VENDOR
        - vendor
        - all
        - {"vendor": "vendor_company-a"} -> {"vendor": ["company-a"]}
      * - TENANT
        - tenant
        - all
        - {"tenant": "default"} -> {"tenant": ["default"]}


Create users with special roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this user guide, user creates three end-users with admin user:

* ``user-a`` with special roles is used as the experimental group.
* ``user-b`` without special roles is used as the control group.
* ``user-manager`` with special roles and ``manager`` role as manager.


Create users
^^^^^^^^^^^^

#. Create the ``user-a`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-a
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | ebbc6cf1a03d49918c8e408535d87268 |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | e0c0212d3a21473da9a9828bb73000fe |
    | name                | user-a                           |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+


#. Create the ``user-b`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-b
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | ebbc6cf1a03d49918c8e408535d87268 |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | d08df8befcfb4d0eb8acd3a88aa62641 |
    | name                | user-b                           |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+


#. Create the ``user-manager`` user:

   .. code-block:: console

    $ openstack user create --project nfv --password devstack user-manager
    +---------------------+----------------------------------+
    | Field               | Value                            |
    +---------------------+----------------------------------+
    | default_project_id  | ebbc6cf1a03d49918c8e408535d87268 |
    | domain_id           | default                          |
    | enabled             | True                             |
    | id                  | ccc5c486a6504918b776a2de8f34deb9 |
    | name                | user-manager                     |
    | options             | {}                               |
    | password_expires_at | None                             |
    +---------------------+----------------------------------+


Create roles
^^^^^^^^^^^^

#. Create the ``AREA_tokyo@japan`` role:

   .. code-block:: console

    $ openstack role create AREA_tokyo@japan
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | 81bd97ee20ef420482b34669cbffe9fd |
    | name        | AREA_tokyo@japan                 |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``AREA_all@all`` role:

   .. code-block:: console

    $ openstack role create AREA_all@all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | 9cbb968d907a4dab8be1af081a9a15fa |
    | name        | AREA_all@all                     |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``VENDOR_company-a`` role:

   .. code-block:: console

    $ openstack role create VENDOR_company-a
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | b4fabd4bed784f60a8b07bd5f3a91a4a |
    | name        | VENDOR_company-a                 |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``VENDOR_all`` role:

   .. code-block:: console

    $ openstack role create VENDOR_all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | aa9fe93854724cd7880d3974dd0e89ef |
    | name        | VENDOR_all                       |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``TENANT_tenant-a`` role:

   .. code-block:: console

    $ openstack role create TENANT_tenant-a
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | e6535546ea42472eb923300617532ad1 |
    | name        | TENANT_tenant-a                  |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``TENANT_all`` role:

   .. code-block:: console

    $ openstack role create TENANT_all
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | d420e279711d49fb8a2f211d816507ec |
    | name        | TENANT_all                       |
    | options     | {}                               |
    +-------------+----------------------------------+


#. Create the ``manager`` role:

   .. code-block:: console

    $ openstack role create manager
    +-------------+----------------------------------+
    | Field       | Value                            |
    +-------------+----------------------------------+
    | description | None                             |
    | domain_id   | None                             |
    | id          | d4bc947fca0f41368ade7173a9f0f9cb |
    | name        | manager                          |
    | options     | {}                               |
    +-------------+----------------------------------+


   .. note::

     In versions 2023.2 and later, the manager role is created by default
     on the keystone side.
     If it has already been created, there is no need to create it
     manually.


Assign roles to user-project pairs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Assign ``AREA_tokyo@japan``, ``VENDOR_company-a`` and ``TENANT_tenant-a``
   to ``user-a``:

   .. code-block:: console

    $ openstack role add --user user-a --project nfv AREA_tokyo@japan
    $ openstack role add --user user-a --project nfv VENDOR_company-a
    $ openstack role add --user user-a --project nfv TENANT_tenant-a


   Verify the role assignment of ``user-a``:

   .. code-block:: console

    $ openstack role assignment list --user user-a --project nfv --names
    +------------------+----------------+-------+-------------+--------+--------+-----------+
    | Role             | User           | Group | Project     | Domain | System | Inherited |
    +------------------+----------------+-------+-------------+--------+--------+-----------+
    | VENDOR_company-a | user-a@Default |       | nfv@Default |        |        | False     |
    | AREA_tokyo@japan | user-a@Default |       | nfv@Default |        |        | False     |
    | TENANT_tenant-a  | user-a@Default |       | nfv@Default |        |        | False     |
    +------------------+----------------+-------+-------------+--------+--------+-----------+


#. Assign reader to ``user-b``:

   .. code-block:: console

    $ openstack role add --user user-b --project nfv reader


   Verify the role assignment of ``user-b``:

   .. code-block:: console

    $ openstack role assignment list --user user-b --project nfv --names
    +--------+----------------+-------+-------------+--------+--------+-----------+
    | Role   | User           | Group | Project     | Domain | System | Inherited |
    +--------+----------------+-------+-------------+--------+--------+-----------+
    | reader | user-b@Default |       | nfv@Default |        |        | False     |
    +--------+----------------+-------+-------------+--------+--------+-----------+


#. Assign ``AREA_all@all``, ``VENDOR_all``, ``TENANT_all`` and
   ``manager`` to ``user-manager``:

   .. code-block:: console

    $ openstack role add --user user-manager --project nfv AREA_all@all
    $ openstack role add --user user-manager --project nfv VENDOR_all
    $ openstack role add --user user-manager --project nfv TENANT_all
    $ openstack role add --user user-manager --project nfv manager


   Verify the role assignment of ``user-manager``:

   .. code-block:: console

    $ openstack role assignment list --user user-manager --project nfv --names
    +---------------+----------------------+-------+-------------+--------+--------+-----------+
    | Role          | User                 | Group | Project     | Domain | System | Inherited |
    +---------------+----------------------+-------+-------------+--------+--------+-----------+
    | VENDOR_all    | user-manager@Default |       | nfv@Default |        |        | False     |
    | TENANT_all    | user-manager@Default |       | nfv@Default |        |        | False     |
    | AREA_all@all  | user-manager@Default |       | nfv@Default |        |        | False     |
    | manager       | user-manager@Default |       | nfv@Default |        |        | False     |
    +---------------+----------------------+-------+-------------+--------+--------+-----------+


Create resources with enhanced tacker attributes
------------------------------------------------

This section describes how to create resources with enhanced tacker
attributes, using examples.


Register vim with area attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When registering a vim, users can specify area attribute for the vim. This is
achieved by putting the area attribute into the extra field of the vim
configuration file. Please refer to :doc:`/cli/cli-legacy-vim` for how
to register a vim.
And the project_name of the vim configuration file is used as tenant attribute
of instantiated VNF.

.. warning::

  It is highly recommended that users who performs the VIM registration is
  isolated from users who call VNF LCM APIs. Otherwise, users can ignore
  area attribute if VIM by overwriting.


#. Register an OpenStack VIM with area attribute ``tokyo@japan``.

   Sample ``vim_config.yaml`` file for OpenStack VIM:

   .. code-block:: yaml

    auth_url: 'http://192.168.56.10/identity/v3'
    username: 'vim-user'
    password: 'devstack'
    project_name: 'tenant-a'
    project_domain_name: 'default'
    user_domain_name: 'default'
    cert_verify: 'True'
    extra:
        area: tokyo@japan


   .. note::

    The project and VIM user which specified in the vim configuration file must
    be created previously and assign the member role to VIM user.


    .. code-block:: console

     $ openstack project create tenant-a --domain default
     $ openstack user create --project tenant-a --password devstack vim-user
     $ openstack role add --user vim-user --project tenant-a member


   Register OpenStack VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_config.yaml \
      --description 'openstack vim in nfv' openstack-tokyo@japan
    +----------------+-----------------------------------------------------+
    | Field          | Value                                               |
    +----------------+-----------------------------------------------------+
    | auth_cred      | {                                                   |
    |                |     "username": "vim-user",                         |
    |                |     "user_domain_name": "default",                  |
    |                |     "cert_verify": "True",                          |
    |                |     "project_id": null,                             |
    |                |     "project_name": "tenant-a",                     |
    |                |     "project_domain_name": "default",               |
    |                |     "auth_url": "http://192.168.56.10/identity/v3", |
    |                |     "key_type": "barbican_key",                     |
    |                |     "secret_uuid": "***",                           |
    |                |     "password": "***"                               |
    |                | }                                                   |
    | auth_url       | http://192.168.56.10/identity/v3                    |
    | created_at     | 2023-12-12 06:49:16.994225                          |
    | description    | openstack vim in nfv                                |
    | extra          | area=tokyo@japan                                    |
    | id             | b266493d-1782-4b4e-9c92-65b0946fe81c                |
    | is_default     | False                                               |
    | name           | openstack-tokyo@japan                               |
    | placement_attr | {                                                   |
    |                |     "regions": [                                    |
    |                |         "RegionOne"                                 |
    |                |     ]                                               |
    |                | }                                                   |
    | project_id     | ebbc6cf1a03d49918c8e408535d87268                    |
    | status         | ACTIVE                                              |
    | type           | openstack                                           |
    | updated_at     | None                                                |
    | vim_project    | {                                                   |
    |                |     "name": "tenant-a",                             |
    |                |     "project_domain_name": "default"                |
    |                | }                                                   |
    +----------------+-----------------------------------------------------+


#. Register a OpenStack VIM with area attribute ``osaka@japan``.

   Sample ``vim_config.yaml`` file for OpenStack VIM:

   .. code-block:: yaml

    auth_url: 'http://192.168.56.10/identity/v3'
    username: 'vim-user'
    password: 'devstack'
    project_name: 'tenant-a'
    project_domain_name: 'default'
    user_domain_name: 'default'
    cert_verify: 'True'
    extra:
        area: osaka@japan


   Register OpenStack VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_config.yaml \
      --description 'openstack vim in nfv' openstack-osaka@japan
    +----------------+-----------------------------------------------------+
    | Field          | Value                                               |
    +----------------+-----------------------------------------------------+
    | auth_cred      | {                                                   |
    |                |     "username": "vim-user",                         |
    |                |     "user_domain_name": "default",                  |
    |                |     "cert_verify": "True",                          |
    |                |     "project_id": null,                             |
    |                |     "project_name": "tenant-a",                     |
    |                |     "project_domain_name": "default",               |
    |                |     "auth_url": "http://192.168.56.10/identity/v3", |
    |                |     "key_type": "barbican_key",                     |
    |                |     "secret_uuid": "***",                           |
    |                |     "password": "***"                               |
    |                | }                                                   |
    | auth_url       | http://192.168.56.10/identity/v3                    |
    | created_at     | 2023-12-12 06:55:57.154779                          |
    | description    | openstack vim in nfv                                |
    | extra          | area=osaka@japan                                    |
    | id             | e0941ab7-dd35-4d08-80ea-1264c75050f4                |
    | is_default     | False                                               |
    | name           | openstack-osaka@japan                               |
    | placement_attr | {                                                   |
    |                |     "regions": [                                    |
    |                |         "RegionOne"                                 |
    |                |     ]                                               |
    |                | }                                                   |
    | project_id     | ebbc6cf1a03d49918c8e408535d87268                    |
    | status         | ACTIVE                                              |
    | type           | openstack                                           |
    | updated_at     | None                                                |
    | vim_project    | {                                                   |
    |                |     "name": "tenant-a",                             |
    |                |     "project_domain_name": "default"                |
    |                | }                                                   |
    +----------------+-----------------------------------------------------+


#. Register a Kubernetes VIM with area attribute ``tokyo@japan``.

   Sample ``vim_config_k8s.yaml`` file for Kubernetes VIM:

   .. code-block:: yaml

    auth_url: "https://192.168.56.10:6443"
    bearer_token: "eyJhbGciOiJSUzI1NiIsImtpZCI6IkdVazBPakx4Q2NsUjJjNHhsZFdaaXJMSHVQMUo4NkdMS0toamlSaENiVFUifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tazhzdmltIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImRlZmF1bHQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiJhNTIzYzFhMi1jYmU5LTQ1Y2YtYTc5YS00ZDA4MDYwZDE3NmEiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkZWZhdWx0In0.BpKAAQLjXMIpJIjqQDsGtyh1a-Ij8e-YOVRv0md_iOGXd1KLR-qreM6xA-Ni8WFILzq3phaZU6npET8PlfhQ6csF5u20OT2SoZ7iAotHXpCcYkRdrUd2oO5KxSFTkOhasaN1pQ3pZyaFYUZbwwmLK3I31rG4Br2VbZQ7Qu8wFOXUK-syBGF48vIPZ5JQ3K00KNxpuEcGybMK5LtdSKZ25Ozp_I2oqm3KBZMPMfWwaUnvuRnyly13tsiXudPt_9H78AxLubMo3rcvECJU2y_zZLiavcZKXAz-UmHulxtz_XZ80hMu-XOpYWEYrOB0Lt0hB59ZoY1y3OvJElTfPyrwWw"
    ssl_ca_cert: "-----BEGIN CERTIFICATE-----
    MIIDBTCCAe2gAwIBAgIIa76wZDxLNAowDQYJKoZIhvcNAQELBQAwFTETMBEGA1UE
    AxMKa3ViZXJuZXRlczAeFw0yMzExMDYwMDA3MzBaFw0zMzExMDMwMDEyMzBaMBUx
    EzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
    AoIBAQDd0LBXGxVexr09mVFNSXWQq3TN66IIcXCBAMbIWI4EiQ8Y0zI4hSwADdK2
    ltYSdWw7wq3/YTFHK8/YTY7Jvd9/k3UJrqkZ6kBtL20pJUPXNJVLE/hRzsqEnHHv
    cfqYZTHvTY4g7qNcMOcfl/oDUGUMfpQT2gs6xoNl0WX/1+QeQbadx1kWaD2Ii45F
    d8TR+c4wccxNaLArk3ok4h1PNeAwra4mRmBHQQ2wFjkTYGl4+ss3v1yoUJkrQjXL
    RgzLufeXaz8eRTi36HkjudGKfS3OnUeke3uBN7usW58FFJ8TdKOhuoguRm53kj6+
    TwXtZCOPzn4gNxq6xJE1Xj2hwFfpAgMBAAGjWTBXMA4GA1UdDwEB/wQEAwICpDAP
    BgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBRdmQ4r63pXBHIO8ODqxROE7x+aizAV
    BgNVHREEDjAMggprdWJlcm5ldGVzMA0GCSqGSIb3DQEBCwUAA4IBAQBeQ/9+bzRe
    qbA02MfYnN3vycGhDObcAoiDIMIutojFTpx4hGZjqVgTRpLH5ReddwR4kkxn3NRg
    weCVkNkhzyGze64nb11qZG71olaOQRMYzyN2hYfmbq7MXSvmJQQYIr1OewaRk+xl
    TyG1XRXoD2IEaHEvG0+pQJlDerd5Z6S1fkPaKZtcRbM/E6y5VXMV6hegN4MwHZSI
    Ll1uEBTxUzzTm3dnl1KL8GDg05ajoYcyL3X/0aWsb/MFhtIlXe2CMxu5qUkLBhzy
    fCfX4cZpI5KFxMgdmAEoaGbNy7iqsGrLFtEmub2gdEBIVNr7vgOk4OeQ9Uodj6K7
    jK97z+cupc5G
    -----END CERTIFICATE-----"
    project_name: "default"
    type: "kubernetes"
    extra:
        use_helm: true
        area: tokyo@japan


   Register Kubernetes VIM:

   .. code-block:: console

    $ openstack vim register --config-file ./vim_k8s_config.yaml \
      --description 'kubernetes vim in nfv' \
      kubernetes-tokyo@japan --fit-width
    +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Field          | Value                                                                                                                                                                                                                                     |
    +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | auth_cred      | {                                                                                                                                                                                                                                         |
    |                |     "bearer_token": "***",                                                                                                                                                                                                                |
    |                |     "ssl_ca_cert": "b'gAAAAABleAUrM8oGbXIoXuHIe3WXU0AXqqe0UdOD9hPECuKMum_7dZwjMx_Xtd6pVMIKXoraXr_x-n1P6wPahwz2V7zt5Mpiy3guplnlfb8qwyUT51yS3JkgEvykXRIwIWvJKBFr2LKU4qGBqmyml8C-ZM7qFN_U9ctyzw53dw0c1Sq7ma19gsUM2Ehbfylz3B4zV_t2aY-         |
    |                | 0a7sA8FBwM_mkmOeL2DjOmHn39TAUeT59zshJSGaKafvGdUb2YOdXp4k6vVB4UR09GmIOlRuFAPfM5_0EhFPQ9Ys1jn-1Q4KCBWXt68yHOoUaepe_zEmLfCn0lAAXdYAjALnymZ8q4xpLI1oY8NsPAM7inMo9NGSGW6Gtb1JegMcYL5-xGjKUfHMKOF5gcndKMNSvkcCEMVcJ6bvheE6eFluFA5QQLLshl-       |
    |                | wYU7eSlM9mapGzlwuCv5QLafuvttiOSn0tgDf3PFuMF9K1BN1Pao-2_A6QwmLqEOwoShUJbD8d7J3ZZykTaBgNOVQSK6IzQKxGZ0ajSqZhPPFrbSYMuTmXCcmGz-G71tPcupSohsf9DNmIVrb8Ylwz50oHr4mB_hrN1LxuUOh-27nawPFwhdeF0_ebqJesjWbYQea6M2JLcHcZs8lrk6w7f4PZN8FFdGa-        |
    |                | s_oOCdxHtM4A4ZQQEDi9IpPc-ekXtxqax5T_8Fve8kBneixYguc9oFffHF195L-0aAJwoo2d5TOYuU2-fhxfGwsfcThGcHpNL3M-giGPGveqgUpc-YoW2HmXtyE0dent_Xc8HFklBfKVNIs2ckP8zgBqx_4h0U09WCsLNKvghXtJy27j0lzo5u5QnIzb7xJjaBcZAAoSsmJvbWlDmcMNENHXKmrzv0qz5uHJ05PBU |
    |                | L7xInxSOfqEPjRK5FccBzpZ9FgWlALvnW7E37PmWrPJyx1g0-rAsOXthFad9Pz3CLQExbly5Z4lQkdqh4YgCbnERL0052_EAILsf9ou-67CHYLcAosZvnU5T2tBTYYUxJWujoJD95OrG9fj-XY7rkAElUe5bIfFj2yf7Kp8jKjaTeXDFZIu5dA9Qk5LPqfxhxSEbL83pmjbuXydO7dXBzmqsameJ0Ju0CmUvsn1rg |
    |                | QjCW899ckRIZH8IvsJM_kVpGoS9m8hnoJwilhuvvAMNQiZqb8qgwb4ooYRryxFOO-6xOaT3joYWryVpeYp9Enmu1LlRPOaV1_Te4f84JK5PYdyJ03-                                                                                                                        |
    |                | KchdiylzSQQsWqs285ZxCssjr_FmSfAs0bf8YnBfbhLmYxgCpopyTuqbPTZf2yqZAlzyhEZf02lzFeJQTETjNyG4HUkQV1yEagoUWbxeozSPaJpatm3D3Bf1Sr-Q_8TspgXZYy9Wws1Ig3aCzs1AW7EczwJFnlBrYlNr1WoTWgk87_ElfyLxuuXfn3Ks-                                             |
    |                | BVzHnciBWjOwmP0CTCJB1MBpARxuqms0KyrxXKJvQbfW9VmQ4kvbrHW227g_SEen1WVfrp27hmJ4wk9WwzrnVGfg8STKHvKW-AoNdpRvuXD07Hjzl1bQaZ0Oee6ngmkPQgCF4N1Sx1vidX-Hg=='",                                                                                    |
    |                |     "auth_url": "https://192.168.56.10:6443",                                                                                                                                                                                             |
    |                |     "username": "None",                                                                                                                                                                                                                   |
    |                |     "key_type": "barbican_key",                                                                                                                                                                                                           |
    |                |     "secret_uuid": "***"                                                                                                                                                                                                                  |
    |                | }                                                                                                                                                                                                                                         |
    | auth_url       | https://192.168.56.10:6443                                                                                                                                                                                                                |
    | created_at     | 2023-12-12 07:00:59.413587                                                                                                                                                                                                                |
    | description    | kubernetes vim in nfv                                                                                                                                                                                                                     |
    | extra          | area=tokyo@japan, use_helm=True                                                                                                                                                                                                           |
    | id             | e5f9e74b-7c58-4316-8523-3617a704d5dc                                                                                                                                                                                                      |
    | is_default     | False                                                                                                                                                                                                                                     |
    | name           | kubernetes-tokyo@japan                                                                                                                                                                                                                    |
    | placement_attr | {                                                                                                                                                                                                                                         |
    |                |     "regions": [                                                                                                                                                                                                                          |
    |                |         "default",                                                                                                                                                                                                                        |
    |                |         "kube-node-lease",                                                                                                                                                                                                                |
    |                |         "kube-public",                                                                                                                                                                                                                    |
    |                |         "kube-system"                                                                                                                                                                                                                     |
    |                |     ]                                                                                                                                                                                                                                     |
    |                | }                                                                                                                                                                                                                                         |
    | project_id     | ebbc6cf1a03d49918c8e408535d87268                                                                                                                                                                                                          |
    | status         | ACTIVE                                                                                                                                                                                                                                    |
    | type           | kubernetes                                                                                                                                                                                                                                |
    | updated_at     | None                                                                                                                                                                                                                                      |
    | vim_project    | {                                                                                                                                                                                                                                         |
    |                |     "name": "default"                                                                                                                                                                                                                     |
    |                | }                                                                                                                                                                                                                                         |
    +----------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Create VNF package with vendor attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The vendor attribute of the VNF package resource comes from the provider field
defined in ``Definitions/vnfd_top.yaml`` of the VNF package. To create a VNF
package with a specified vendor attribute, users need to modify the provider
attribute to vendor. Please refer to :doc:`/user/vnf-package` for how to
make zip file and create VNF packages. This chapter only gives a sample of
configuration files that need to be modified in VNF package.

#. Set the provider in ``Definitions/vnfd_top.yaml`` to ``company-a``.

   .. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2

    description: Sample VNF

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml
      - sample_vnfd_types.yaml
      - sample_vnfd_df_simple.yaml

    topology_template:
      inputs:
        selected_flavour:
          type: string
          description: VNF deployment flavour selected by the consumer. It is provided in the API

      node_templates:
        VNF:
          type: company.provider.VNF
          properties:
            flavour_id: { get_input: selected_flavour }
            descriptor_id: c1bb0ce7-ebca-4fa7-95ed-4840d70a1175
            provider: company-a
            product_name: Sample VNF
            software_version: "1.0"
            descriptor_version: "1.0"
            vnfm_info:
              - Tacker
          requirements:
            #- virtual_link_external # mapped in lower-level templates
            #- virtual_link_internal # mapped in lower-level templates


#. Set the provider in ``Definitions/vnfd_types.yaml`` to ``company-a``.

   .. code-block:: yaml

    tosca_definitions_version: tosca_simple_yaml_1_2

    description: VNF type definition

    imports:
      - etsi_nfv_sol001_common_types.yaml
      - etsi_nfv_sol001_vnfd_types.yaml

    node_types:
      company.provider.VNF:
        derived_from: tosca.nodes.nfv.VNF
        properties:
          ...
          provider:
            type: string
            constraints: [valid_values: ["company-a"]]
            default: "company-a"
          ...


Create & Instantiate VNF with vendor, area and tenant attributes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create VNF with vendor attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The vendor attribute of the VNF comes from the provider attribute of the VNF
package. Therefore, users only need to use the VNF package with the specified
provider attribute to create a VNF with the specified vendor attribute.

The following is an example of creating a VNF with the specified vendor
attribute.

Create a VNF with vnfd_id:

.. code-block:: console

  $ openstack vnflcm create <vnfd_id>


Instantiate VNF on VIM with area and tenant attributes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The area and tenant attribute of the VNF comes from the used vim. In other
words, you need to specify a VIM in the area and tenant where you want to
instantiate a VNF.

For VNF LCM API version 1, please refer to :doc:`/cli/cli-etsi-vnflcm` to
instantiate VNF. Below are two samples of <param-file>.

#. If <param-file> contains the ``vimConnectionInfo`` parameter, the area
   and tenant attributes come from vim in it.

   .. code-block:: json

     {
         "flavourId": "simple",
         "vimConnectionInfo": [
             {
                 "id": "e24f9796-a8e9-4cb0-85ce-5920dcddafa1",
                 "vimId": "9f2bac4c-2d17-4269-8164-93d4e875f101",
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_2"
             }
         ]
     }


#. If <param-file> doesn't contains the ``vimConnectionInfo`` parameter, the
   default vim is used and area and tenant attributes come from it.

   .. code-block:: json

     {
         "flavourId": "simple"
     }


For VNF LCM API version 2, please refer to :doc:`/cli/cli-etsi-vnflcm` to
instantiate VNF. Below are two samples of <param-file>.

#. If the vim in the ``vimConnectionInfo`` parameter of <param-file> is an
   existing vim in the DB, the area and tenant attribute of the instantiated
   VNF comes from this vim.

   .. code-block:: json

     {
         "flavourId": "simple",
         "vimConnectionInfo": {
             "vim1": {
                 "id": "725f625e-f6b7-4bcd-b1b7-7184039fde45"
                 "vimId": "9f2bac4c-2d17-4269-8164-93d4e875f101",
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3"
             }
         }
     }


#. If the vim in the ``vimConnectionInfo`` parameter of <param-file> is not
   existed in the DB, users need to specify the area and tenant attributes in
   the ``vimConnectionInfo`` parameter. The tenant attribute uses the
   ``project`` in the ``accessInfo`` of the ``vimConnectionInfo``.

   .. code-block:: json

     {
         "flavourId": "simple",
         "vimConnectionInfo": {
             "vim1": {
                 "accessInfo": {
                     "password": "devstack",
                     "project": "tenant-a",
                     "projectDomain": "Default",
                     "region": "RegionOne",
                     "userDomain": "Default",
                     "username": "vim-user"
                 },
                 "interfaceInfo": {
                     "endpoint": "http://localhost/identity/v3"
                 },
                 "vimId": "03e608b2-e7d4-44fa-bd84-74fb24be3ed5",
                 "vimType": "ETSINFV.OPENSTACK_KEYSTONE.V_3",
                 "extra": {"area": "tokyo@japan"}
             }
         }
     }


Instantiate CNF with tenant attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When instantiating CNF, the tenant attribute of CNF is specified by the
namespace in the additionalParams field of <param-file>.

.. code-block:: json

  {
      "flavourId": "simple",
      "vimConnectionInfo": [
          {
              "id": "b1bb0ce7-ebca-4fa7-95ed-4840d70a1177",
              "vimId": "43a2c212-8a6b-468f-a51f-c912fdd722fe",
              "vimType": "kubernetes"
          }
      ],
      "additionalParams": {
          "lcm-kubernetes-def-files": [
              "Files/kubernetes/deployment.yaml",
              "Files/kubernetes/namespace.yaml"
          ],
          "namespace": "tenant-a"
      }
  }


Usage of APIs supporting Enhanced Tacker Policy
-----------------------------------------------

This section takes the VIM Management API as an example to introduce the API
calls that support Enhanced Tacker Policy. You can find a list of APIs that
support Enhanced Tacker Policy and the enhanced tacker attributes supported by
each API in `Tacker APIs that support Enhanced Tacker Policy`_.


GET individual resources
~~~~~~~~~~~~~~~~~~~~~~~~

Users with special roles have permission to access corresponding resources. For
example, ``user-a`` who has the role of ``AREA_tokyo@japan`` has permission
to access the VIM with area attribute ``tokyo@japan``. ``user-b`` who does
not have the role of ``AREA_tokyo@japan`` does not have permission to
access the VIM with area attribute ``tokyo@japan``. Here take Show VIM as
an example.

``user-a`` shows VIM whose area attribute is ``tokyo@japan``, and it succeeds.

.. code-block:: console

  $ openstack vim show 9f2bac4c-2d17-4269-8164-93d4e875f101
  +----------------+-----------------------------------------------------+
  | Field          | Value                                               |
  +----------------+-----------------------------------------------------+
  | auth_cred      | {                                                   |
  |                |     "username": "vim-user",                         |
  |                |     "user_domain_name": "default",                  |
  |                |     "cert_verify": "True",                          |
  |                |     "project_id": null,                             |
  |                |     "project_name": "tenant-a",                     |
  |                |     "project_domain_name": "default",               |
  |                |     "auth_url": "http://192.168.56.10/identity/v3", |
  |                |     "key_type": "barbican_key",                     |
  |                |     "secret_uuid": "***",                           |
  |                |     "password": "***"                               |
  |                | }                                                   |
  | auth_url       | http://192.168.56.10/identity/v3                    |
  | created_at     | 2024-01-05 02:10:30                                 |
  | description    | openstack vim in nfv                                |
  | extra          | area=tokyo@japan                                    |
  | id             | 9f2bac4c-2d17-4269-8164-93d4e875f101                |
  | is_default     | True                                                |
  | name           | openstack-tokyo@japan                               |
  | placement_attr | {                                                   |
  |                |     "regions": [                                    |
  |                |         "RegionOne"                                 |
  |                |     ]                                               |
  |                | }                                                   |
  | project_id     | 711fcdc235bf4095bb83fe368a4f95a6                    |
  | status         | ACTIVE                                              |
  | type           | openstack                                           |
  | updated_at     | 2024-01-05 03:11:24                                 |
  | vim_project    | {                                                   |
  |                |     "name": "tenant-a",                             |
  |                |     "project_domain_name": "default"                |
  |                | }                                                   |
  +----------------+-----------------------------------------------------+


``user-b`` shows VIM whose area attribute is ``tokyo@japan``, and it fails.

.. code-block:: console

  $ openstack vim show 9f2bac4c-2d17-4269-8164-93d4e875f101
  Unable to find vim with name '9f2bac4c-2d17-4269-8164-93d4e875f101'


Users can use the ``manager`` role to distinguish between reference APIs and
operating APIs. This is an existing function of oslo.policy, and here is just a
suggested usage scenario.

``user-a`` has no ``manager`` role and cannot delete VIM.

.. code-block:: console

  $ openstack vim delete 9f2bac4c-2d17-4269-8164-93d4e875f101


  Unable to delete the below vim(s):
  Cannot delete 9f2bac4c-2d17-4269-8164-93d4e875f101: Unable to find vim with name '9f2bac4c-2d17-4269-8164-93d4e875f101'


``user-manager`` has the role of ``manager`` and can delete VIM.

.. code-block:: console

  $ openstack vim delete 9f2bac4c-2d17-4269-8164-93d4e875f101
  All specified vim(s) deleted successfully


.. note::

  Please note that currently, the "openstack vim show/set/delete"
  commands do not work properly due to the following bug.

  * https://bugs.launchpad.net/tacker/+bug/2051069

  The API below itself works correctly.

  * GET /v1.0/vims/{vim_id}
  * PUT /v1.0/vims/{vim_id}
  * Delete /v1.0/vims/{vim_id}


LIST resources
~~~~~~~~~~~~~~

For APIs that list resources, Enhanced Tacker Policy acts as a filter. That is,
the list operation only lists resources that the user has permission.
Here take List VIM as an example.

The ``user-a`` only has permission to access the VIM with area attribute
``tokyo@japan``. Therefore, ``user-a`` can only list the VIM with area
attribute ``tokyo@japan``.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name                   | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+
  | 43a2c212-8a6b-468f-a51f-c912fdd722fe | kubernetes-tokyo@japan | 711fcdc235bf4095bb83fe368a4f95a6 | kubernetes | False      | ACTIVE |
  | 9f2bac4c-2d17-4269-8164-93d4e875f101 | openstack-tokyo@japan  | 711fcdc235bf4095bb83fe368a4f95a6 | openstack  | False      | ACTIVE |
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+


The ``user-b`` does not have access to any VIM with the area attribute, so
the list is empty when performing the List VIM operation.

.. code-block:: console

  $ openstack vim list
  (No output.)


The ``user-manager`` has access rights to all resources. It can list all
resources.

.. code-block:: console

  $ openstack vim list
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+
  | ID                                   | Name                   | Tenant_id                        | Type       | Is Default | Status |
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+
  | 43a2c212-8a6b-468f-a51f-c912fdd722fe | kubernetes-tokyo@japan | 711fcdc235bf4095bb83fe368a4f95a6 | kubernetes | False      | ACTIVE |
  | 9f2bac4c-2d17-4269-8164-93d4e875f101 | openstack-tokyo@japan  | 711fcdc235bf4095bb83fe368a4f95a6 | openstack  | False      | ACTIVE |
  | c100874d-26f6-4b34-b0eb-55bfaba926aa | openstack-osaka@japan  | 711fcdc235bf4095bb83fe368a4f95a6 | openstack  | False      | ACTIVE |
  +--------------------------------------+------------------------+----------------------------------+------------+------------+--------+


Limitations
-----------
* As the resources created in the previous version of Tacker may not have
  enhanced policy attributes, if the enhanced policy attributes are used as
  comparison attributes in the policy rule, this rule will prevent users from
  accessing those resources without these attributes as the comparison result
  is always false.


Appendix
--------

Tacker APIs that support Enhanced Tacker Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The table below lists the APIs that support Enhanced Tacker Policy, and the
enhanced tacker attributes supported by each API.

.. list-table::
  :widths: 28 28 16 16 16
  :header-rows: 1

  * - Operation
    - API
    - Supports area
    - Supports vendor
    - Supports tenant
  * - VIM-List
    - **GET** /v1.0/vims
    - Yes
    - No
    - No
  * - VIM-Show
    - **GET** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - VIM-Update
    - **PUT** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - VIM-Delete
    - **Delete** /v1.0/vims/{vim_id}
    - Yes
    - No
    - No
  * - PKG-List
    - **GET** /vnfpkgm/v1/vnf_packages
    - No
    - Yes(1)
    - No
  * - PKG-Show
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes(1)
    - No
  * - PKG-Update
    - **PATCH** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes
    - No
  * - PKG-Delete
    - **DELETE** /vnfpkgm/v1/vnf_packages/{vnfPkgId}
    - No
    - Yes
    - No
  * - PKG-Read-vnfd
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/vnfd
    - No
    - Yes
    - No
  * - PKG-Fetch
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/package_content
    - No
    - Yes
    - No
  * - PKG-Upload-content
    - **PUT** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/package_content
    - No
    - Yes
    - No
  * - PKG-Artifacts
    - **GET** /vnfpkgm/v1/vnf_packages/{vnfPkgId}/artifacts/{artifactPath}
    - No
    - Yes
    - No
  * - LCM-List
    - **GET** /vnflcm/v1/vnf_instances
    - Yes(2)
    - Yes
    - Yes(3)
  * - LCM-Create
    - **POST** /vnflcm/v1/vnf_instances
    - No
    - Yes
    - No
  * - LCM-Show
    - **GET** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - Yes(2)
    - Yes
    - Yes(3)
  * - LCM-Update
    - **PATCH** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - Yes
    - Yes
    - Yes
  * - LCM-Delete
    - **DELETE** /vnflcm/v1/vnf_instances/{vnfInstanceId}
    - No
    - Yes
    - No
  * - LCM-Instantiate
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/instantiate
    - No
    - Yes
    - No
  * - LCM-Scale
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/scale
    - Yes
    - Yes
    - Yes
  * - LCM-Terminate
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/terminate
    - Yes
    - Yes
    - Yes
  * - LCM-Heal
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/heal
    - Yes
    - Yes
    - Yes
  * - LCM-Change-Connectivity
    - **POST** /vnflcm/v1/vnf_instances/{vnfInstanceId}/change_ext_conn
    - Yes
    - Yes
    - Yes
  * - LCM-ListV2
    - **GET** /vnflcm/v2/vnf_instances
    - Yes(3)
    - Yes
    - Yes(3)
  * - LCM-CreateV2
    - **POST** /vnflcm/v2/vnf_instances
    - No
    - Yes
    - No
  * - LCM-ShowV2
    - **GET** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - Yes(3)
    - Yes
    - Yes(3)
  * - LCM-UpdateV2
    - **PATCH** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - Yes
    - Yes
    - Yes
  * - LCM-DeleteV2
    - **DELETE** /vnflcm/v2/vnf_instances/{vnfInstanceId}
    - No
    - Yes
    - No
  * - LCM-InstantiateV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/instantiate
    - No
    - Yes
    - No
  * - LCM-ScaleV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/scale
    - Yes
    - Yes
    - Yes
  * - LCM-TerminateV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/terminate
    - Yes
    - Yes
    - Yes
  * - LCM-HealV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/heal
    - Yes
    - Yes
    - Yes
  * - LCM-Change-ConnectivityV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/change_ext_conn
    - Yes
    - Yes
    - Yes
  * - LCM-Change-VnfPkgV2
    - **POST** /vnflcm/v2/vnf_instances/{vnfInstanceId}/change_vnfpkg
    - Yes
    - Yes
    - Yes

(1) This is ignored when the state is not `ONBOARDED`.
(2) Default vim is used when the state is `NOT_INSTANTIATED`.
(3) This is ignored when the state is `NOT_INSTANTIATED`.


Sample policy.yaml file
~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../../etc/tacker/enhanced_tacker_policy.yaml.sample


.. _oslo.policy: https://docs.openstack.org/oslo.policy/latest/
