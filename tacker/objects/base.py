#    Copyright 2018 NTT DATA.
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

from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base

from tacker import objects


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    return '_obj_' + name


class TackerObjectRegistry(ovoo_base.VersionedObjectRegistry):
    notification_classes = []

    def registration_hook(self, cls, index):
        # NOTE(bhagyashris): This is called when an object is registered,
        # and is responsible for maintaining tacker.objects.$OBJECT
        # as the highest-versioned implementation of a given object.
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            cur_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= cur_version:
                setattr(objects, cls.obj_name(), cls)


class TackerObject(ovoo_base.VersionedObject):
    # NOTE(bhagyashris): OBJ_PROJECT_NAMESPACE needs to be set so that nova,
    # tacker, and other objects can exist on the same bus and be distinguished
    # from one another.
    OBJ_SERIAL_NAMESPACE = 'tacker_object'
    OBJ_PROJECT_NAMESPACE = 'tacker'
