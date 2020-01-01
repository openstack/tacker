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

import contextlib
import datetime

import oslo_messaging as messaging
from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import exception as ovoo_exc

from tacker import objects
from tacker.objects import fields as obj_fields


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

    def __init__(self, context=None, **kwargs):
        super(TackerObject, self).__init__(context, **kwargs)
        self.obj_set_defaults()

    def tacker_obj_get_changes(self):
        """Returns a dict of changed fields with tz unaware datetimes.

        Any timezone aware datetime field will be converted to UTC timezone
        and returned as timezone unaware datetime.

        This will allow us to pass these fields directly to a db update
        method as they can't have timezone information.
        """
        # Get dirtied/changed fields
        changes = self.obj_get_changes()

        # Look for datetime objects that contain timezone information
        for k, v in changes.items():
            if isinstance(v, datetime.datetime) and v.tzinfo:
                # Remove timezone information and adjust the time according to
                # the timezone information's offset.
                changes[k] = v.replace(tzinfo=None) - v.utcoffset()

        # Return modified dict
        return changes

    def obj_reset_changes(self, fields=None, recursive=False):
        """Reset the list of fields that have been changed.

        .. note::

          - This is NOT "revert to previous values"
          - Specifying fields on recursive resets will only be honored at the
            top level. Everything below the top will reset all.

        :param fields: List of fields to reset, or "all" if None.
        :param recursive: Call obj_reset_changes(recursive=True) on
                          any sub-objects within the list of fields
                          being reset.
        """
        if recursive:
            for field in self.obj_get_changes():

                # Ignore fields not in requested set (if applicable)
                if fields and field not in fields:
                    continue

                # Skip any fields that are unset
                if not self.obj_attr_is_set(field):
                    continue

                value = getattr(self, field)

                # Don't reset nulled fields
                if value is None:
                    continue

                # Reset straight Object and ListOfObjects fields
                if isinstance(self.fields[field], obj_fields.ObjectField):
                    value.obj_reset_changes(recursive=True)
                elif isinstance(self.fields[field],
                                obj_fields.ListOfObjectsField):
                    for thing in value:
                        thing.obj_reset_changes(recursive=True)

        if fields:
            self._changed_fields -= set(fields)
        else:
            self._changed_fields.clear()

    @contextlib.contextmanager
    def obj_alternate_context(self, context):
        original_context = self._context
        self._context = context
        try:
            yield
        finally:
            self._context = original_context


class TackerObjectSerializer(messaging.NoOpSerializer):
    """A TackerObject-aware Serializer.

    This implements the Oslo Serializer interface and provides the
    ability to serialize and deserialize TackerObject entities. Any service
    that needs to accept or return TackerObjects as arguments or result values
    should pass this to its RPCClient and RPCServer objects.
    """

    def _process_object(self, context, objprim):
        try:
            objinst = TackerObject.obj_from_primitive(objprim, context=context)
        except ovoo_exc.IncompatibleObjectVersion:
            raise
        return objinst

    def _process_iterable(self, context, action_fn, values):
        """Process an iterable, taking an action on each value.

        :param:context: Request context
        :param:action_fn: Action to take on each item in values
        :param:values: Iterable container of things to take action on
        :returns: A new container of the same type (except set) with
                  items from values having had action applied.
        """

        iterable = values.__class__
        if issubclass(iterable, dict):
            return iterable(**{k: action_fn(context, v)
                               for k, v in values.items()})
        else:
            # NOTE(nirajsingh) A set can't have an unhashable value inside,
            # such as a dict. Convert the set to list, which is fine, since we
            # can't send them over RPC anyway. We convert it to list as this
            # way there will be no semantic change between the fake rpc driver
            # used in functional test and a normal rpc driver.
            if iterable == set:
                iterable = list
            return iterable([action_fn(context, value) for value in values])

    def serialize_entity(self, context, entity):
        if isinstance(entity, (tuple, list, set, dict)):
            entity = self._process_iterable(context, self.serialize_entity,
                                            entity)
        elif (hasattr(entity, 'obj_to_primitive') and
              callable(entity.obj_to_primitive)):
            entity = entity.obj_to_primitive()
        return entity

    def deserialize_entity(self, context, entity):
        if isinstance(entity, dict) and 'tacker_object.name' in entity:
            entity = self._process_object(context, entity)
        elif isinstance(entity, (tuple, list, set, dict)):
            entity = self._process_iterable(context, self.deserialize_entity,
                                            entity)
        return entity


class TackerPersistentObject(object):
    """Mixin class for Persistent objects.

    This adds the fields that we use in common for most persistent objects.
    """
    fields = {
        'created_at': obj_fields.DateTimeField(nullable=False),
        'updated_at': obj_fields.DateTimeField(nullable=True),
        'deleted_at': obj_fields.DateTimeField(nullable=True),
        'deleted': obj_fields.BooleanField(default=False)
    }


remotable = ovoo_base.remotable
remotable_classmethod = ovoo_base.remotable_classmethod
obj_make_list = ovoo_base.obj_make_list
TackerObjectDictCompat = ovoo_base.VersionedObjectDictCompat
