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


import collections
import contextlib
import datetime

from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_serialization import jsonutils
from oslo_utils import versionutils
from oslo_versionedobjects import base as ovoo_base
from oslo_versionedobjects import exception as ovoo_exc

from tacker.db import api as db_api
from tacker.sol_refactored.db.sqlalchemy import models
from tacker.sol_refactored import objects
from tacker.sol_refactored.objects import fields as obj_fields


LOG = logging.getLogger(__name__)


def get_attrname(name):
    """Return the mangled name of the attribute's underlying storage."""
    return '_obj_' + name


# Every TackerObject has its attributes named exactly same as the corresponding
# ETSI NFV-SOL data type attributes. In almost all cases, so as its one-to-one
# mapped model attributes and DB column names. However, some field names
# cannot be used for model attributes (e.g., 'metadata'), in which case we
# append a suffix '__' (double underscores) as a workaround.
#
# Note that TackerObject users need not to concern about this.
#
# Example:
# - NFV-SOL data type "VnfXXX"
#     - id
#     - name
#     - metadata
# - class VnfXXX(base.TackerPersistentObject) attributes
#     - id
#     - name
#     - metadata
# - class VnfXXX(model_base.BASE) attributes
#     - id
#     - name
#     - metadata__  <-- 'metadata' is one of reserved names and cannot be used.
# - DB column names:
#     - id
#     - name
#     - metadata
RESERVED_FIELD_NAMES = [
    'metadata',
]


def get_model_field(name):
    if name in RESERVED_FIELD_NAMES:
        return name + '__'
    return name


class TackerObjectRegistry(ovoo_base.VersionedObjectRegistry):
    notification_classes = []
    _registry = None

    # NOTE: Separate registry from original tacker objects.
    # When original tacker objects are gone, _registry and
    # __new__ can be removed.
    def __new__(cls, *args, **kwargs):
        if not TackerObjectRegistry._registry:
            TackerObjectRegistry._registry = object.__new__(
                TackerObjectRegistry, *args, **kwargs)
            TackerObjectRegistry._registry._obj_classes = \
                collections.defaultdict(list)
        self = object.__new__(cls, *args, **kwargs)
        self._obj_classes = TackerObjectRegistry._registry._obj_classes
        return self

    def registration_hook(self, cls, index):
        # NOTE: This is called when an object is registered,
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
    # These should be renamed (s/_sol_refactored//) when the older
    # implementation ceases to exist.
    OBJ_SERIAL_NAMESPACE = 'tacker_sol_refactored_object'
    OBJ_PROJECT_NAMESPACE = 'tacker_sol_refactored'

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
                elif isinstance(self.fields[field],
                                obj_fields.DictOfObjectsField):
                    for key, thing in value.items():
                        thing.obj_reset_changes(recursive=True)

        if fields:
            self._changed_fields -= set(fields)
        else:
            self._changed_fields.clear()

    @classmethod
    def from_dict(cls, dict_obj):
        inst = cls()
        for name, field in cls.fields.items():
            value = dict_obj.get(name, None)
            if value is None:
                continue
            if isinstance(field, obj_fields.ObjectField):
                child_cls = cls.obj_class_from_name(field.objname, cls.VERSION)
                setattr(inst, name, child_cls.from_dict(value))
            elif isinstance(field, obj_fields.ListOfObjectsField):
                child_cls = cls.obj_class_from_name(field.objname, cls.VERSION)
                list_of_objects = []
                for thing in value:
                    list_of_objects.append(child_cls.from_dict(thing))
                setattr(inst, name, list_of_objects)
            elif isinstance(field, obj_fields.DictOfObjectsField):
                child_cls = cls.obj_class_from_name(field.objname, cls.VERSION)
                dict_of_objects = {}
                for key, thing in value.items():
                    dict_of_objects[key] = child_cls.from_dict(thing)
                setattr(inst, name, dict_of_objects)
            else:
                setattr(inst, name, field.from_primitive(inst, name, value))
        return inst

    @classmethod
    def from_json(cls, json_obj):
        return cls.from_dict(jsonutils.loads(json_obj))

    def to_dict(self):
        obj = {}
        for name, field in self.fields.items():
            if not self.obj_attr_is_set(name):
                continue
            if getattr(self, name) is None:
                continue
            if isinstance(field, obj_fields.ObjectField):
                obj[name] = getattr(self, name).to_dict()
            elif isinstance(field, obj_fields.ListOfObjectsField):
                obj[name] = []
                for item in getattr(self, name):
                    obj[name].append(item.to_dict())
            elif isinstance(field, obj_fields.DictOfObjectsField):
                obj[name] = {}
                for key, item in getattr(self, name).items():
                    obj[name][key] = item.to_dict()
            else:
                obj[name] = field.to_primitive(self, name, getattr(self, name))
        return obj

    def to_json(self):
        return jsonutils.dumps(self.to_dict())

    @contextlib.contextmanager
    def obj_alternate_context(self, context):
        original_context = self._context
        self._context = context
        try:
            yield
        finally:
            self._context = original_context

    @classmethod
    def obj_class_from_name(cls, objname, objver):
        """Returns a class from the registry based on a name and version."""
        if objname not in TackerObjectRegistry.obj_classes():
            LOG.error('Unable to instantiate unregistered object type '
                      '%(objtype)s'), dict(objtype=objname)
            raise ovoo_exc.UnsupportedObjectError(objtype=objname)

        # NOTE: only the newest version is registered by registration_hook.
        # omit version check.
        return TackerObjectRegistry.obj_classes()[objname][0]


class TackerObjectSerializer(messaging.NoOpSerializer):
    """A TackerObject-aware Serializer.

    This implements the Oslo Serializer interface and provides the
    ability to serialize and deserialize TackerObject entities. Any service
    that needs to accept or return TackerObjects as arguments or result values
    should pass this to its RPCClient and RPCServer objects.
    """

    def _process_object(self, context, objprim):
        return TackerObject.obj_from_primitive(objprim, context=context)

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

        # NOTE: A set can't have an unhashable value inside,
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
        if (isinstance(entity, dict) and
                TackerObject._obj_primitive_key('name') in entity):
            entity = self._process_object(context, entity)
        elif isinstance(entity, (tuple, list, set, dict)):
            entity = self._process_iterable(context, self.deserialize_entity,
                                            entity)
        return entity


class TackerPersistentObject(TackerObject):
    """Class for objects supposed to be to DB."""

    def __init__(self, context=None, **kwargs):
        super(TackerPersistentObject, self).__init__(context, **kwargs)
        self._db_obj = None

    # By default, it's assumed that there is a model class corresponding to one
    # TackerPersistentObject, which has the same named fields.
    def _get_model_cls(self):
        clsname = self.__class__.__name__
        return getattr(models, clsname)

    @db_api.context_manager.writer
    def _save(self, context, merge=False):
        if not self.obj_get_changes():
            return
        model_cls = self._get_model_cls()
        inst = model_cls()
        inst.update(self.to_db_obj())
        # note: The same workaround is present in oslo.db ModelBase.save()
        #       implementation.
        with context.session.begin(subtransactions=True):
            if merge:
                context.session.merge(inst, load=True)
            else:
                context.session.add(inst)
            context.session.flush()
        # 'flush' must have succeeded because we are here.
        if self._db_obj is None:
            self._db_obj = inst
        self.obj_reset_changes()

    @db_api.context_manager.writer
    def delete(self, context):
        if self._db_obj is None:
            return
        context.session.delete(self._db_obj)

    # WARNING: Check if it is really necessary if you consider overriding this.
    def create(self, context):
        self._save(context)

    # WARNING: Check if it is really necessary if you consider overriding this.
    def update(self, context):
        self._save(context, merge=True)

    @classmethod
    @db_api.context_manager.reader
    def get_by_id(cls, context, id):
        model_cls = getattr(models, cls.__name__)
        query = context.session.query(model_cls).filter(model_cls.id == id)
        result = query.one_or_none()
        if result is None:
            return None
        return cls.from_db_obj(result)

    @classmethod
    @db_api.context_manager.reader
    def get_all(cls, context):
        model_cls = getattr(models, cls.__name__)
        query = context.session.query(model_cls)
        result = query.all()
        return [cls.from_db_obj(item) for item in result]

    @classmethod
    @db_api.context_manager.reader
    def get_by_filter(cls, context, *args, **kwargs):
        model_cls = getattr(models, cls.__name__)
        query = context.session.query(model_cls).filter_by(**kwargs)
        result = query.all()
        return [cls.from_db_obj(item) for item in result]

    @classmethod
    def from_db_obj(cls, db_obj):
        inst = cls()
        for name, field in cls.fields.items():
            name_ = get_model_field(name)
            value = db_obj.get(name_, None)
            if value is None:
                continue
            if isinstance(field, obj_fields.ObjectField):
                child_cls = cls.obj_class_from_name(field.objname, None)
                setattr(inst, name, child_cls.from_json(value))
            elif isinstance(field, obj_fields.ListOfObjectsField):
                child_cls = cls.obj_class_from_name(field.objname, None)
                list_of_objects = []
                value_loaded = jsonutils.loads(value)
                for thing in value_loaded:
                    list_of_objects.append(child_cls.from_dict(thing))
                setattr(inst, name, list_of_objects)
            elif isinstance(field, obj_fields.DictOfObjectsField):
                child_cls = cls.obj_class_from_name(field.objname, None)
                dict_of_objects = {}
                value_loaded = jsonutils.loads(value)
                for key, thing in value_loaded.items():
                    dict_of_objects[key] = child_cls.from_dict(thing)
                setattr(inst, name, dict_of_objects)
            elif isinstance(field, obj_fields.DateTimeField):
                setattr(inst, name, value)
            else:
                setattr(inst, name, field.from_primitive(inst, name, value))
        inst._db_obj = db_obj
        inst.obj_reset_changes()
        return inst

    def to_db_obj(self):
        obj = {}
        for name, field in self.fields.items():
            name_ = get_model_field(name)
            if not self.obj_attr_is_set(name):
                continue
            if getattr(self, name) is None:
                obj[name_] = None
                continue
            if isinstance(field, obj_fields.ObjectField):
                obj[name_] = getattr(self, name).to_json()
            elif isinstance(field, obj_fields.ListOfObjectsField):
                list_of_objects = []
                for item in getattr(self, name):
                    list_of_objects.append(item.to_dict())
                obj[name_] = jsonutils.dumps(list_of_objects)
            elif isinstance(field, obj_fields.DictOfObjectsField):
                dict_of_objects = {}
                for key, item in getattr(self, name).items():
                    dict_of_objects[key] = item.to_dict()
                obj[name_] = jsonutils.dumps(dict_of_objects)
            elif isinstance(field, obj_fields.DateTimeField):
                obj[name_] = getattr(self, name)
            else:
                obj[name_] = field.to_primitive(self, name,
                                                getattr(self, name))
        return obj


TackerObjectDictCompat = ovoo_base.VersionedObjectDictCompat
