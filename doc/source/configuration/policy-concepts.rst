Understanding Tacker Policies
=============================

Tacker supports RBAC policy system to control the access permission of APIs.
Tacker RBAC policy rule have the default value which can be overridden by
operators via ``policy.yaml`` file.

We try to make the policy default value as close to operators requirements.
In the Tacker 11.0.0 (OpenStack 2024.1 caracal) release, further work was
undertaken to address some issues that had been identified:

#. No read-only roles. Since several APIs tend to share a single policy rule
   for read and write actions, they did not provide the granularity necessary
   for read-only access roles. To solve this, we should have reader role in
   the policy.

#. The ``admin_or_owner`` rule did not work as expected. It has check_str
   ``"is_admin:True or project_id:%(project_id)s",`` which means it only
   check project_id for owner and not any role. This means `admin_or_owner``
   rule will allow user with any role in project. For example, user with
   ``role:foo`` in project will behaves as the owner of the project resources.
   To solve this we should also check the ``member`` role in ``admin_or_owner``
   rule.

Keystone comes with ``admin``, ``member`` and ``reader`` roles by default.
Please refer to `keystone document
<https://docs.openstack.org/keystone/latest//admin/service-api-protection.html>`_
for more information about these new defaults. In addition, keystone supports
a new "scope" concept that makes it easier to protect deployment level
resources from project level resources. Please refer to `keystone authorization
scopes document
<https://docs.openstack.org/keystone/latest//admin/tokens-overview.html#authorization-scopes>`_
to understand the scope concept.

In the Tacker 11.0.0 (OpenStack 2024.1 caracal), Tacker policies implemented
the new default roles provided by keystone (admin, member, and reader). Using
common roles from keystone reduces the likelihood of similar, but different,
roles implemented across projects or deployments (e.g., a role called
``observer`` versus ``reader`` versus ``auditor``). With the help of the new
defaults it is easier to understand who can do what across projects, reduces
divergence, and increases interoperability. Along with new defaults, Tacker
policy define scope_type which is hardcoded to ``project`` so that if system
scope token try to access the Tacker APIs, they can get better error message.

The below sections explain how these new defaults in the Tacker can solve the
two issues mentioned above and extend more functionality to end users in a
safe and secure way.

Scope
-----

OpenStack `Keystone supports different scopes
<https://docs.openstack.org/keystone/latest//admin/tokens-overview.html#authorization-scopes>`_
in tokens. Token scopes represent the layer of authorization. Policy
``scope_types`` represent the layer of authorization required to access an API.

.. note::

     The ``scope_type`` of each policy is hardcoded  to ``project`` scoped
     and is not overridable via the policy file.

Tacker policies have implemented the scope concept by defining the
``scope_type`` for all the policies to ``project`` scoped. It means if user
tries to access Tacker APIs with ``system`` scoped token they will get 403
permission denied error.

For example, consider the ``POST /vnflcm/v1/vnf_instances`` API.

.. code::

    # Creates a new VNF instance resource
    # POST  /vnflcm/v1/vnf_instances
    # Intended scope(s): project
    #"os_nfv_orchestration_api:vnf_instances:create": "rule:project_member_or_admin"

Policy scope is disabled by default to allow operators to migrate from the
old policy enforcement system in a graceful way. This can be enabled by
configuring the :oslo.config:option:`oslo_policy.enforce_scope` option to
``True`` in tacker.conf on controller node.

.. note::

  [oslo_policy]
  enforce_scope=True


Roles
-----

You can refer to `keystone role documentation
<https://docs.openstack.org/keystone/latest//admin/service-api-protection.html>`_
to know about all available defaults from Keystone.

Tacker policy defines new defaults for each policy.

.. rubric:: ``reader``

This provides read-only access to the resources. Tacker policies are
defaulted to below rules:

.. code-block:: python

    policy.RuleDefault(
        name="admin_api",
        check_str="role:admin",
        description="Default rule for administrative APIs."
    )

    policy.RuleDefault(
        name="project_reader",
        check_str="role:reader and project_id:%(project_id)s",
        description="Default rule for Project level read only APIs."
    )

Using it in policy rule (with admin + reader access): (because we want to
keep legacy admin behavior the same we need to give access of reader APIs
to admin role too.)

.. code-block:: python

    policy.DocumentedRuleDefault(
        name='os_nfv_orchestration_api:vnf_instances:show',
        check_str='role:admin or (' + 'role:reader and project_id:%(project_id)s)',
        description="Query an Individual VNF instance.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    )

OR

.. code-block:: python

    policy.DocumentedRuleDefault(
        name='os_nfv_orchestration_api:vnf_instances:show',
        check_str='rule: admin or rule:project_reader',
        description="Query an Individual VNF instance.",
        operations=[
            {
                'method': 'GET',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    )

.. rubric:: ``member``

project-member is denoted by someone with the member role on a project. It is
intended to be used by end users who consume resources within a project which
requires higher permission than reader role but less than admin role. It
inherits all the permissions of a project-reader.

project-member persona in the policy check string:

.. code-block:: python

    policy.RuleDefault(
        name="admin_api",
        check_str="role:admin",
        description="Default rule for administrative APIs."
    )

    policy.RuleDefault(
        name="project_member",
        check_str="role:member and project_id:%(project_id)s",
        description="Default rule for Project level non admin APIs."
    )

Using it in policy rule (with admin + member access): (because we want to keep
legacy admin behavior, admin role gets access to the project level member APIs.)

.. code-block:: python

    policy.DocumentedRuleDefault(
        name='os_nfv_orchestration_api:vnf_instances:create',
        check_str='role:admin or (' + 'role:member and project_id:%(project_id)s)',
        description="Creates vnf instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    )

OR

.. code-block:: python

    policy.DocumentedRuleDefault(
        name='os_nfv_orchestration_api:vnf_instances:create',
        check_str='rule: admin or rule:project_member',
        description="Query an Individual VNF instance.",
        operations=[
            {
                'method': 'POST',
                'path': '/vnflcm/v1/vnf_instances/{vnfInstanceId}'
            }
        ],
        scope_types=['project'],
    )

'project_id:%(project_id)s' in the check_str is important to restrict the
access within the requested project.

.. rubric:: ``admin``

This role is to perform the admin level write operations. Tacker policies are
defaulted to below rules:

.. code-block:: python

   policy.DocumentedRuleDefault(
       name='Polciy name',
       check_str='role:admin',
       scope_types=['project']
   )

Tacker supported scope & Roles
------------------------------

Tacker supports the below combination of scopes and roles where roles can
be overridden in the policy.yaml file but scope is not override-able.

#. ADMIN: ``admin`` role on ``project`` scope. This is an administrator to
   perform the admin level operations.

#. PROJECT_MEMBER: ``member`` role on ``project`` scope. This is used to
   perform resource owner level operation within project. For example:
   create vnf instance.

#. PROJECT_READER: ``reader`` role on ``project`` scope. This is used to
   perform read-only operation within project. For example: Get vnf instance.

#. PROJECT_MEMBER_OR_ADMIN: ``admin`` or ``member`` role on ``project`` scope.
   Such policy rules are default to most of the owner level APIs and align
   with `member` role legacy admin can continue to access those APIs.

#. PROJECT_READER_OR_ADMIN: ``admin`` or ``reader`` role on ``project`` scope.
   Such policy rules are default to most of the read only APIs so that legacy
   admin can continue to access those APIs.

Backward Compatibility
----------------------

Backward compatibility with versions prior to Tacker 11.0.0 (OpenStack
2024.1 Caracal) is maintained by supporting the old defaults by default.
This means the old defaults and deployments that use them will keep working
as-is. However, we encourage every deployment to switch to the new policy.
The new defaults will be enabled by default in Tacker 12.0.0 (OpenStack
2024.2 Dalmatian) release but we will keep the old default in deprecated
defaults will be removed starting in the Tacker 15.0.0 (OpenStack 2026.1)
release.

Migration Plan
--------------

To have a graceful migration, Tacker provides two flags to switch to the new
policy completely. You do not need to overwrite the policy file to adopt the
new policy defaults.

Here is step wise guide for migration:

#. Create scoped token:

   You need to create the project scoped token via below CLI:

   - `Create Project Scoped Token
     <https://docs.openstack.org/keystone/latest//admin/tokens-overview.html#operation_create_project_scoped_token>`_.

#. Create new default roles in keystone if not done:

   If you do not have new defaults in Keystone then you can create and re-run
   the `Keystone Bootstrap <https://docs.openstack.org/keystone/latest//admin/bootstrap.html>`_.

#. Enable Scope Checks

   The :oslo.config:option:`oslo_policy.enforce_scope` flag is to enable the
   ``scope_type`` features. The scope of the token used in the request is
   always compared to the ``scope_type`` of the policy. If the scopes do not
   match, one of two things can happen.
   If :oslo.config:option:`oslo_policy.enforce_scope` is True, the request
   will be rejected. If  :oslo.config:option:`oslo_policy.enforce_scope` is
   False, an warning will be logged, but the request will be accepted
   (assuming the rest of the policy passes). The default value of this flag
   is False.

#. Enable new defaults

   The :oslo.config:option:`oslo_policy.enforce_new_defaults` flag switches
   the policy to new defaults-only. This flag controls whether or not to use
   old deprecated defaults when evaluating policies. If True, the old
   deprecated defaults are not evaluated. This means if any existing token
   is allowed for old defaults but is disallowed for new defaults, it will be
   rejected. The default value of this flag is False.

   .. note:: Before you enable this flag, you need to educate users about the
             different roles they need to use to continue using Tacker APIs.

NOTE::

  We recommend to enable the both scope as well new defaults together
  otherwise you may experience some late failures with unclear error
  messages. For example, if you enable new defaults and disable scope
  check then it will allow system users to access the APIs but fail
  later due to the project check which can be difficult to debug.

Below table show how legacy rules are mapped to new rules:

+--------------------+---------------------------+----------------+-----------+
| Legacy Rule        |    New Rules              |Operation       |scope_type |
+====================+===========================+================+===========+
| RULE_ADMIN_API     |-> ADMIN                   |Global resource | [project] |
|                    |                           |Write & Read    |           |
+--------------------+---------------------------+----------------+-----------+
|                    |-> ADMIN                   |Project admin   | [project] |
|                    |                           |level operation |           |
|                    +---------------------------+----------------+-----------+
| RULE_ADMIN_OR_OWNER|-> PROJECT_MEMBER_OR_ADMIN |Project resource| [project] |
|                    |                           |Write           |           |
|                    +---------------------------+----------------+-----------+
|                    |-> PROJECT_READER_OR_ADMIN |Project resource| [project] |
|                    |                           |Read            |           |
+--------------------+---------------------------+----------------+-----------+

We expect all deployments to migrate to the new policy by Tacker
13.0.0 (OpenStack 2025.1) release so that we can remove the support
of old policies in future release.
