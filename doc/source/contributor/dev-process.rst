Tacker Development Process
==========================

.. include:: ../../../CONTRIBUTING.rst

Enhancement to Tacker functionality can be done using one of the following
two development process options. The choice depends on the complexity of the
enhancement.

Request for Enhancement (RFE) Process
-------------------------------------

The developer, or an operator, can write up the requested enhancement in a
Tacker launchpad [#]_ bug.

* The requester need to mark the bug with "RFE" tag.
* The bug will be in the initial "New" state.
* The requester and team will have a discussion on the enhancement in the
  launchpad bug.
* Once the discussion is over a tacker-core team member will acknowledge the
  validity of this feature enhancement by moving it to the "Confirmed" state.
* Developers submit patchsets to implement the enhancement using the bug-id.
  Note, if there are multiple patchsets Partial-Bug header should be used
  instead of Closes-Bug in the commit message.
* Once all the patchsets are merged the bug will be moved to the "Completed"
  state.
* Developer(s) are expected to add a devref describing the usage of the feature
  and other related topics in tacker/doc/source/contributor directory.

This process is recommended for smaller enhancements that can be described
easily and it is relatively easy to implement in a short period of time.

Blueprint and Tacker-Specs process
----------------------------------

The developer, or an operator, can write up the requested enhancement by
submitting a patchset to the tacker-spec repository [#]_.

* The patchset should follow the template specified in [#]_
* The requester should also create a corresponding blueprint for the
  enhancement proposal in launchpad [#]_
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
  and other related topics in tacker/doc/source/contributor directory.

This process is recommended for medium to large enhancements that needs
significant code-changes (LOC), community discussions and debates.

References
----------

.. [#] https://bugs.launchpad.net/tacker
.. [#] https://github.com/openstack/tacker-specs
.. [#] https://github.com/openstack/tacker-specs/blob/master/specs/template.rst
.. [#] https://blueprints.launchpad.net/tacker/
