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

"""Fixtures for Tacker unit tests."""
# NOTE(bhagyashris): This is needed for importing from fixtures.

import warnings

import fixtures as pyfixtures


class WarningsFixture(pyfixtures.Fixture):
    """Filters out warnings during test runs."""

    def setUp(self):
        super(WarningsFixture, self).setUp()
        # NOTE(bhagyashris): user/tenant is deprecated in oslo.context
        # so don't let anything new use it
        warnings.filterwarnings(
            'error', message="Property '.*' has moved to '.*'")

        self.addCleanup(warnings.resetwarnings)
