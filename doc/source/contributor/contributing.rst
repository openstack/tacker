============================
So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects: the
accounts you need, the basics of interacting with our Gerrit review system,
how we communicate as a community, etc.


The official Tacker source code is available in following repositories:

* **Tacker server:** https://opendev.org/openstack/tacker
* **Tacker Python client:** https://opendev.org/openstack/python-tackerclient
* **Tacker Horizon UI:** https://opendev.org/openstack/tacker-horizon

Below will cover the more project specific information you need to get started
with Tacker.

Communication
~~~~~~~~~~~~~
* IRC channel ``#tacker`` at `Freenode`_
* Mailing list (prefix subjects with ``[tacker]`` for faster responses)
  http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss

All conversations are logged and stored for your
convenience at `eavesdrop.openstack.org`_. For more information regarding
OpenStack IRC channels please visit the `OpenStack IRC Wiki`_.

.. _`Freenode`: https://freenode.net
.. _`OpenStack IRC Wiki`: https://wiki.openstack.org/wiki/IRC
.. _`eavesdrop.openstack.org`: http://eavesdrop.openstack.org/irclogs/%23tacker/

Contacting the Core Team
~~~~~~~~~~~~~~~~~~~~~~~~
Please refer to the `Tacker Core Team
<https://review.opendev.org/#/admin/groups/378,members>`_ contacts.

New Feature Planning
~~~~~~~~~~~~~~~~~~~~
If you want to propose a new feature, Tacker features are tracked on
`Launchpad BP`_.

Enhancement to Tacker functionality can be done using one of the following
two development process options. The choice depends on the complexity of the
enhancement.

Request for Enhancement (RFE) Process
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The developer, or an operator, can write up the requested enhancement in
Tacker's `Launchpad Bugs`_.

* The requester needs to mark the bug with ``RFE`` tag.
* The bug will be in the initial "New" state.
* The requester and team will have a discussion on the enhancement in the
  launchpad bug.
* Once the discussion is over a tacker-core team member will acknowledge the
  validity of this feature enhancement by moving it to the "Confirmed" state.
* Developers submit patchsets to fix a bug using ``Closes-Bug`` with **bug-id**
  in the commit message.
  Note, if there are multiple patchsets ``Partial-Bug`` header should be used
  instead of ``Closes-Bug``.
* Once all the patchsets are merged the bug will be moved to the "Completed"
  state.
* Developer(s) are expected to add a devref describing the usage of the feature
  and other related topics in "tacker/doc/source/contributor directory".

This process is recommended for smaller enhancements that can be described
easily and it is relatively easy to implement in a short period of time.

Blueprint and Tacker-Specs process
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The developer, or an operator, can write up the requested enhancement by
submitting a patchset to the `tacker-spec repository`_

* The patchset should follow the `spec template`_
* The requester should also create a corresponding `Launchpad BP`_
  for the enhancement proposal
* The requester and the team will have a discussion on the tacker-spec
  writeup using gerrit.
* The patchset will be merged into the tackers-specs repository if the
  tacker-core team decides this is a valid feature enhancement. A patchset
  may also be rejected with clear reasoning.
* Tacker core team will also mark the blueprint Definition field to Approved.
* Developer submits one or more patchsets to implement the enhancement. The
  commit message should use "Implements: blueprint <blueprint-name>" using
  the same name as the blueprint name.
* Once all the patchsets are merged the blueprint will be as "Implemented" by
  the tacker core team.
* The developer is expected to add a devref describing the usage of the feature
  and other related topics in "tacker/doc/source/contributor directory".

This process is recommended for medium to large enhancements that needs
significant code-changes (LOC), community discussions and debates.

.. _`Launchpad BP`: https://blueprints.launchpad.net/tacker
.. _`Launchpad Bugs`: https://bugs.launchpad.net/tacker
.. _`tacker-spec repository`: https://opendev.org/openstack/tacker-specs
.. _`spec template`: https://opendev.org/openstack/tacker-specs/src/branch/master/specs/template.rst

Task Tracking
~~~~~~~~~~~~~
We track our tasks in `Launchpad
<https://launchpad.net/tacker>`_.
If you're looking for some smaller, easier work item to pick up and get started
on, search for the ``low-hanging-fruit`` tag.

Reporting a Bug
~~~~~~~~~~~~~~~
You found an issue and want to make sure we are aware of it? You can do so on
`Report a bug
<https://bugs.launchpad.net/tacker/+filebug>`_ in Launchpad.
More info about Launchpad usage can be found on `OpenStack docs page
<https://docs.openstack.org/contributors/common/task-tracking.html#launchpad>`_.

Getting Your Patch Merged
~~~~~~~~~~~~~~~~~~~~~~~~~
All changes proposed to Tacker require two +2 votes from core reviewers
before one of the core reviewers can approve patch by giving
``Workflow +1`` vote.
PTL may require more than two +2 votes, depending on the complexity of the
proposal.
More detailed guidelines for reviewers of patches are available at
`Code Review
<https://docs.opendev.org/opendev/infra-manual/latest/developers.html#code-review>`_.

.. note::

    Pull requests submitted through GitHub will be ignored.

Project Team Lead Duties
~~~~~~~~~~~~~~~~~~~~~~~~
All common PTL duties are enumerated in the `PTL guide
<https://docs.openstack.org/project-team-guide/ptl.html>`_.
