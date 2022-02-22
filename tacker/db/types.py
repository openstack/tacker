# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from oslo_serialization import jsonutils

from sqlalchemy.types import String
from sqlalchemy.types import Text
from sqlalchemy.types import TypeDecorator


class Uuid(TypeDecorator):
    impl = String(36)

    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            # If value is typed as List, only use first element.
            if isinstance(value, list):
                value = value[0]
            try:
                uuid.UUID(value, version=4)
            except ValueError:
                raise ValueError(
                    "Invalid format. It should be in UUID v4 format")

        return value

    def process_result_value(self, value, dialect):
        return value


class Json(TypeDecorator):
    impl = Text

    cache_ok = False

    def process_bind_param(self, value, dialect):
        return jsonutils.dump_as_bytes(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return jsonutils.loads(value)
