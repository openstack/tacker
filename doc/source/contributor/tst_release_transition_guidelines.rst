..
      Copyright (C) 2025 NEC, Corp.
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

============================================
TST Release Transition Guidelines for Tacker
============================================

Overview
--------

This document defines the collaboration framework between the TST
(Test Suite Tooling) and Tacker teams to support the transition from one
TST release to another within the Tacker project. The primary objective is
to ensure that Tacker maintains conformance with ETSI NFV SOL
specifications throughout TST release upgrades.

It outlines the definitions and responsibilities of involved teams, the
necessary pre-transition checks, detailed planning and validation methods
for the transition process, procedures for identifying and resolving
specification or implementation gaps and the criteria for completion and
acceptance of the transition.

Background
----------

ETSI SOL Specifications
^^^^^^^^^^^^^^^^^^^^^^^

The ETSI NFV SOL series (e.g., SOL002, SOL003, SOL005, etc.) provides
standardized APIs for NFV orchestration and management. These
specifications enable interoperability between NFV components such as
VIMs, VNFMs, and NFVOs. Tacker aims to conform to these standards as
part of its ongoing development.

TST (Test Suite Tooling)
^^^^^^^^^^^^^^^^^^^^^^^^

TST is an open-source compliance test suite aligned with ETSI NFV SOL
specifications. It validates the conformance of MANO components (like
Tacker) to SOL standards, particularly SOL002, SOL003, and SOL005. Each
TST release (e.g., Rel2, Rel3) corresponds to a version of the ETSI
specification and includes automated test cases and execution tools.

Tacker
^^^^^^^

Tacker is an OpenStack project that implements a generic VNFM (Virtualized
Network Function Manager) and NFVO (NFV Orchestrator) based on ETSI NFV
MANO standards. It supports standardized APIs like SOL002, SOL003, and
SOL005 to enable interoperability and automate the lifecycle management
of VNFs and network services in NFV environments.

Pre-Transition Requirements
---------------------------

Before initiating the transition to a new TST release, ensure the following
prerequisites are met:

1. The targeted TST release has been reviewed and aligns with the
   corresponding ETSI SOL specification version.

2. Target TST release code repository.

3. ETSI SOL Specification Reference (official ETSI NFV SOL specification
   document that the target TST release is designed to validate).

4. Tacker’s current SOL compliance status is well-documented. The
   documentation should detail:

   * SOL versions (e.g., SOL003) that Tacker currently aligns with.
   * Supported operations (e.g., Instantiate, Terminate, Scale, Heal).
   * API endpoints fully implemented (e.g., ``POST /vnf_instances``,
     ``GET /subscriptions``).

Transition Planning
-------------------

The transition from an existing TST release to a newer one should be
planned in coordination between the TST and Tacker teams. Steps include:

1. **Target TST Release Analysis**

   * Analyze the new or target TST release code/documentation to understand:
      * ETSI specification version targeted by the release
      * Major changes from the previous release

   * Identify test cases newly added, modified, or deprecated.

2. **Impact Analysis**

   * Determine the effect of TST changes on Tacker’s existing functionality
     by executing TST target release code with current Tacker compliance
     test code.

   * Identify areas needing development or modification to support the new
     tests.

3. **Local Testing and Validation**

   * After applying necessary code or configuration changes, execute the
     new TST release against a local or development Tacker environment to
     validate functionality.

   * Validate test behavior, log results, and confirm fixes before proceeding.

4. **CI Integration Preparation**

   Once the new or updated Tacker code for target TST release pass successfully
   in the local setup:

   * Integrate the updated code into Tacker’s CI pipeline.
   * Submit a patch for merge and test execution in CI environments.
   * Monitor test results and address any issues that appear in CI.

Test Execution Approaches
-------------------------

Manual Testing
^^^^^^^^^^^^^^

Used primarily during early transition phases or in isolated environments:

1. Install and configure the target TST release manually.
2. Execute tests against a stable Tacker deployment.
3. Record and categorize results (pass/fail/skipped).

CI/CD Integrated Testing
^^^^^^^^^^^^^^^^^^^^^^^^

For continuous feedback and automated validation:

1. Integrate the updated code into Tacker’s CI pipeline (e.g., via Zuul).
2. Configure automated test execution to trigger on patch submissions.
3. Monitor and review test results in the CI dashboard.

.. note::

   CI integration is essential for regression prevention and long-term
   maintenance.

Gap Identification and Reporting
--------------------------------

During the TST release transition, it is essential to identify and track
the root causes of test failures or unexpected behaviors.

Specification Gaps
^^^^^^^^^^^^^^^^^^

A Specification Gap occurs when a test case in the TST suite behaves in a
manner that is inconsistent with the official ETSI NFV SOL specification
it is supposed to validate.

Reporting Steps:

1. Create an issue in the official TST Git repository:
   https://forge.etsi.org/rep/nfv/api-tests/issues

2. Provide detailed information on the issue, including:

   * Relevant SOL section (e.g., SOL003 v3.3.1, clause 7.2.5)
   * Clear description of the observed discrepancy between the TST test
     behavior and the expected behavior defined by the ETSI standard.
   * Supporting evidence such as test output, API traces, or Tacker logs.

Tacker Implementation Gaps
^^^^^^^^^^^^^^^^^^^^^^^^^^

A Tacker Implementation Gap refers to a situation where Tacker fails a TST
test due to any issue or bug in Tacker code which deviates from ETSI
specification.

Reporting Steps:

1. Create a bug or issue in the Tacker Launchpad:
   https://launchpad.net/tacker

2. Provide detailed information on the issue, including:

   * Test case information such as name, id, etc. (as defined in TST).
   * Expected vs. actual behavior, with reference to ETSI specifications
     if applicable.
   * Relevant logs and API traces captured during the test execution.

.. note::

   Optional test cases or those related to unsupported SOL features may be
   skipped with appropriate justification.
