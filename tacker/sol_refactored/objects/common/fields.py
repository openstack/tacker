# Copyright (C) 2021 Nippon Telegraph and Telephone Corporation
# All Rights Reserved.
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

import uuid

from oslo_serialization import jsonutils
from oslo_versionedobjects import fields as ovoo_fields


AutoTypedField = ovoo_fields.AutoTypedField
BaseEnumField = ovoo_fields.BaseEnumField
BooleanField = ovoo_fields.BooleanField
DateTimeField = ovoo_fields.DateTimeField
DictOfStringsField = ovoo_fields.DictOfStringsField
Enum = ovoo_fields.Enum
EnumField = ovoo_fields.EnumField
Field = ovoo_fields.Field
FieldType = ovoo_fields.FieldType
IntegerField = ovoo_fields.IntegerField
IPAddressField = ovoo_fields.IPAddressField
List = ovoo_fields.List
ListOfEnumField = ovoo_fields.ListOfEnumField
ListOfObjectsField = ovoo_fields.ListOfObjectsField
ListOfStringsField = ovoo_fields.ListOfStringsField
MACAddressField = ovoo_fields.MACAddressField
NonNegativeIntegerField = ovoo_fields.NonNegativeIntegerField
ObjectField = ovoo_fields.ObjectField
StringField = ovoo_fields.StringField


class BaseTackerEnum(Enum):
    def __init__(self):
        super(BaseTackerEnum, self).__init__(valid_values=self.__class__.ALL)


class DictOfObjectsField(AutoTypedField):
    def __init__(self, objtype, subclasses=False, **kwargs):
        self.AUTO_TYPE = ovoo_fields.Dict(
            ovoo_fields.Object(objtype, subclasses))
        self.objname = objtype
        super(DictOfObjectsField, self).__init__(**kwargs)


class Jsonable(ovoo_fields.FieldType):
    def coerce(self, obj, attr, value):
        jsonutils.dumps(value)
        return value


# NFV-SOL 013
# - v3.4.1 7.1.5
class KeyValuePairsField(AutoTypedField):
    AUTO_TYPE = ovoo_fields.Dict(Jsonable(), nullable=True)


class ListOfIPAddressesField(AutoTypedField):
    AUTO_TYPE = ovoo_fields.List(ovoo_fields.IPAddress())


class UUID(ovoo_fields.UUID):
    def coerce(self, obj, attr, value):
        uuid.UUID(value)
        return str(value)


class UUIDField(AutoTypedField):
    AUTO_TYPE = UUID()


class ListOfUUIDField(AutoTypedField):
    AUTO_TYPE = ovoo_fields.List(UUID())


class Version(ovoo_fields.StringField):
    pass


class VersionField(AutoTypedField):
    AUTO_TYPE = Version()


class ListOfVersionsField(AutoTypedField):
    AUTO_TYPE = ovoo_fields.List(Version())


class Uri(ovoo_fields.String):
    pass


class UriField(AutoTypedField):
    AUTO_TYPE = Uri()


class Checksum(ovoo_fields.String):
    pass


class ChecksumField(AutoTypedField):
    AUTO_TYPE = Checksum()
